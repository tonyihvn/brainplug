"""Action execution service."""
import uuid
import requests
import smtplib
import logging
import yaml
import io
import csv
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from backend.models import db
from backend.models.action import ScheduledActivity, ActionHistory, Report
from backend.models.settings import DatabaseSetting, APIConfig
from backend.utils.logger import setup_logger
from backend.utils.database import DatabaseConnector
from backend.utils.url_reader import URLReader
from backend.services.result_formatter import ResultFormatter

logger = setup_logger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()


class ActionService:
    """Service for executing various actions."""
    
    def __init__(self):
        """Initialize action service."""
        self.db_connector = DatabaseConnector()
        self.url_reader = URLReader()
        self.result_formatter = ResultFormatter()
    
    def _parse_parameters(self, parameters):
        """
        Parse parameters from either dict or YAML string format.
        
        Args:
            parameters: Either a dict or YAML string
        
        Returns:
            Parsed parameters dict
        """
        if isinstance(parameters, dict):
            return parameters
        
        if isinstance(parameters, str):
            try:
                # Try to parse as YAML
                parsed = yaml.safe_load(parameters)
                if isinstance(parsed, dict):
                    return parsed
                # If YAML parsing returns a list (like in "- url: ...\n  - key:..."), 
                # convert list of dicts to single dict
                if isinstance(parsed, list):
                    result = {}
                    for item in parsed:
                        if isinstance(item, dict):
                            result.update(item)
                    return result
            except yaml.YAMLError:
                pass
            
            try:
                # Try JSON as fallback
                import json
                return json.loads(parameters)
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Return empty dict if parsing fails
        return {}
    
    def _normalize_action_type(self, action_type_raw):
        """Normalize action type (must match llm_service normalization)."""
        if not action_type_raw:
            return 'NONE'
        
        normalized = action_type_raw.lower().strip()
        
        mapping = {
            'database query': 'DATABASE_QUERY',
            'database_query': 'DATABASE_QUERY',
            'db query': 'DATABASE_QUERY',
            'sql': 'DATABASE_QUERY',
            'display data': 'DISPLAY_DATA',
            'display_data': 'DISPLAY_DATA',
            'email': 'EMAIL',
            'url read': 'URL_READING',
            'url_reading': 'URL_READING',
            'api call': 'API_CALL',
            'api_call': 'API_CALL',
            'schedule': 'SCHEDULED_ACTIVITY',
            'report': 'REPORT',
            'procedural plan': 'PROCEDURAL_PLAN',
            'procedural_plan': 'PROCEDURAL_PLAN',
            'none': 'NONE',
        }
        
        if normalized in mapping:
            return mapping[normalized]
        
        return normalized.upper().replace(' ', '_')
    
    def execute_action(self, action_data, conversation_id=None):
        """
        Execute an action based on type and parameters.
        
        Args:
            action_data: Dictionary with action type and parameters
            conversation_id: Associated conversation ID
        
        Returns:
            Action execution result
        """
        try:
            # Normalize the action type first
            action_type = action_data.get('type', 'NONE')
            action_type_normalized = self._normalize_action_type(action_type)
            logger.info(f"execute_action: Received '{action_type}' → Normalized to '{action_type_normalized}'")
            action_data['type'] = action_type_normalized
            
            action_id = str(uuid.uuid4())

            # Enforce allowed action types to avoid LLM-generated exotic types
            allowed_actions = {
                'DATABASE_QUERY', 'DISPLAY_DATA', 'PROCEDURAL_PLAN', 'EMAIL', 'URL_READING',
                'API_CALL', 'SCHEDULED_ACTIVITY', 'REPORT', 'NONE'
            }
            if action_type_normalized not in allowed_actions:
                raise ValueError(f"Unknown or disallowed action type: {action_type_normalized}. Allowed: {', '.join(sorted(allowed_actions))}")
            
            # Record action history
            history = ActionHistory(
                id=action_id,
                conversation_id=conversation_id,
                action_type=action_type_normalized,
                action_data=action_data,
                status='executing'
            )
            db.session.add(history)
            db.session.commit()
            
            result = None
            
            if action_type_normalized == 'DATABASE_QUERY':
                result = self._execute_database_query(action_data)
            elif action_type_normalized == 'DISPLAY_DATA':
                result = self._execute_display_data(action_data)
            elif action_type_normalized == 'PROCEDURAL_PLAN':
                result = self._execute_procedural_plan(action_data, conversation_id=conversation_id)
            elif action_type_normalized == 'EMAIL':
                result = self._execute_email(action_data)
            elif action_type_normalized == 'URL_READING':
                result = self._execute_url_read(action_data)
            elif action_type_normalized == 'API_CALL':
                result = self._execute_api_call(action_data)
            elif action_type_normalized == 'SCHEDULED_ACTIVITY':
                result = self._execute_schedule(action_data)
            elif action_type_normalized == 'REPORT':
                result = self._generate_report(action_data)
            elif action_type_normalized == 'NONE':
                result = {'status': 'skipped', 'message': 'No action required'}
            else:
                raise ValueError(f"Unknown action type: {action_type_normalized}")
            
            # Format the result with 3-level summarization
            formatted_result = self.result_formatter.format_result(result, action_type_normalized)
            logger.info(f"✓ Result formatted - Summary (L1): {formatted_result.get('summary_levels', {}).get('level_1', 'N/A')[:80]}")
            
            # Update history with result - store summary only to avoid DB packet size issues
            history.status = 'success'
            
            # For database queries with large results, store summary levels only
            if action_type_normalized == 'DATABASE_QUERY' and formatted_result.get('row_count', 0) > 100:
                history.result = {
                    'status': 'success',
                    'summary_levels': formatted_result.get('summary_levels', {}),
                    'row_count': formatted_result.get('row_count', 0),
                    'column_count': formatted_result.get('column_count', 0),
                    'truncated': True,
                    'message': 'Large dataset - showing first 100 rows in frontend'
                }
            else:
                history.result = formatted_result
            
            db.session.commit()
            
            return {
                'action_id': action_id,
                'status': 'success',
                'result': formatted_result  # Send formatted result to frontend
            }
        
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            if 'history' in locals():
                history.status = 'failed'
                history.error_message = str(e)
                db.session.commit()
            raise
    
    def _execute_database_query(self, action_data):
        """Execute a database query."""
        try:
            db_name = action_data.get('database', 'default')
            # Support both 'query' and 'sql_query' keys
            query = action_data.get('sql_query') or action_data.get('query')
            
            if not query:
                raise ValueError("Query is required (provide 'sql_query' or 'query')")
            
            # Remove backticks if present
            query = query.strip().strip('`')
            
            logger.info(f"→ Executing database query: {query[:100]}...")
            result = self.db_connector.execute_query(db_name, query)
            
            # Convert datetime objects to ISO format strings for JSON serialization
            serializable_rows = []
            if result:
                for row in result:
                    if isinstance(row, dict):
                        serializable_row = {}
                        for key, value in row.items():
                            # Convert datetime to ISO format string
                            if hasattr(value, 'isoformat'):
                                serializable_row[key] = value.isoformat()
                            else:
                                serializable_row[key] = value
                        serializable_rows.append(serializable_row)
                    else:
                        serializable_rows.append(row)
            
            total_rows = len(serializable_rows)
            logger.info(f"✓ Query executed: {total_rows} rows returned")
            
            # Limit stored result to first 100 rows to avoid MySQL packet size issues
            # Full result will be sent to frontend but truncated for DB storage
            stored_rows = serializable_rows[:100] if len(serializable_rows) > 100 else serializable_rows
            
            return {
                'rows': serializable_rows,  # Send all rows to frontend
                'row_count': total_rows,
                'displayed_rows': len(stored_rows),
                'truncated': total_rows > 100
            }
        
        except Exception as e:
            logger.error(f"Error executing database query: {str(e)}")
            raise
    
    def _execute_email(self, action_data):
        """Execute email sending/reading."""
        try:
            action = action_data.get('action')  # 'send' or 'read'
            
            if action == 'send':
                return self._send_email(action_data)
            elif action == 'read':
                return self._read_emails(action_data)
            else:
                raise ValueError("Invalid email action")
        
        except Exception as e:
            logger.error(f"Error executing email action: {str(e)}")
            raise
    
    def _send_email(self, action_data):
        """Send an email."""
        try:
            from backend.models.settings import DatabaseSetting
            
            # Get SMTP settings
            smtp_settings = DatabaseSetting.query.filter_by(
                db_type='smtp'
            ).first()
            
            if not smtp_settings:
                raise ValueError("SMTP settings not configured")
            
            # Prepare email
            sender = action_data.get('from_email')
            recipient = action_data.get('to_email')
            subject = action_data.get('subject')
            body = action_data.get('body')
            
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_settings.host, smtp_settings.port) as server:
                server.starttls()
                server.login(smtp_settings.username, smtp_settings.password)
                server.send_message(msg)
            
            return {'status': 'sent', 'recipient': recipient}
        
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise
    
    def _read_emails(self, action_data):
        """Read emails from mailbox."""
        # Implementation depends on IMAP/POP configuration
        return {'status': 'read', 'emails_count': 0}
    
    def _execute_url_read(self, action_data):
        """Read and process URL content."""
        try:
            # Try to get URL from direct field first
            url = action_data.get('url')
            
            # If not found, try to parse from parameters
            if not url:
                parameters = action_data.get('parameters')
                if parameters:
                    parsed_params = self._parse_parameters(parameters)
                    url = parsed_params.get('url')
            
            if not url:
                raise ValueError("URL not provided in action_data or parameters")
            
            logger.info(f"URL Reading: {url}")
            action = action_data.get('action', 'read')  # 'read', 'summarize', 'extract'
            
            content = self.url_reader.read_url(url)
            
            if action == 'summarize':
                # Summarize content using LLM
                from backend.services.llm_service import LLMService
                llm = LLMService()
                summary = llm.model.generate_content(
                    f"Summarize this content:\n\n{content[:2000]}"
                ).text
                return {'url': url, 'summary': summary}
            
            return {'url': url, 'content': content[:500]}
        
        except Exception as e:
            logger.error(f"Error executing URL read: {str(e)}")
            raise
    
    def _execute_api_call(self, action_data):
        """Call an external API."""
        try:
            api_name = action_data.get('api_name')
            params = action_data.get('params', {})
            
            api_config = APIConfig.query.filter_by(name=api_name).first()
            if not api_config:
                raise ValueError(f"API config not found: {api_name}")
            
            headers = api_config.headers or {}
            
            # Add authentication
            if api_config.auth_type == 'bearer':
                headers['Authorization'] = f"Bearer {api_config.auth_value}"
            elif api_config.auth_type == 'apikey':
                headers['X-API-Key'] = api_config.auth_value
            
            # Make request
            response = requests.request(
                method=api_config.method,
                url=api_config.endpoint,
                headers=headers,
                params=params
            )
            
            return {
                'api': api_name,
                'status_code': response.status_code,
                'data': response.json() if response.headers.get('content-type') == 'application/json' else response.text
            }
        
        except Exception as e:
            logger.error(f"Error executing API call: {str(e)}")
            raise
    
    def _execute_schedule(self, action_data):
        """Schedule an activity for later execution."""
        try:
            activity_data = action_data.get('activity')
            scheduled_for = datetime.fromisoformat(activity_data.get('scheduled_for'))
            
            activity = ScheduledActivity(
                id=str(uuid.uuid4()),
                title=activity_data.get('title'),
                action_type=activity_data.get('action_type'),
                action_data=activity_data.get('action_data'),
                scheduled_for=scheduled_for,
                recurrence=activity_data.get('recurrence'),
                is_active=True,
                next_execution=scheduled_for
            )
            
            db.session.add(activity)
            db.session.commit()
            
            # Schedule with APScheduler
            if activity_data.get('recurrence'):
                if activity_data['recurrence'] == 'daily':
                    scheduler.add_job(
                        self._execute_scheduled_activity,
                        'interval',
                        hours=24,
                        args=[activity.id],
                        id=activity.id,
                        start_date=scheduled_for
                    )
            else:
                scheduler.add_job(
                    self._execute_scheduled_activity,
                    'date',
                    run_date=scheduled_for,
                    args=[activity.id],
                    id=activity.id
                )
            
            return {
                'activity_id': activity.id,
                'scheduled_for': scheduled_for.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error scheduling activity: {str(e)}")
            raise
    
    def _execute_scheduled_activity(self, activity_id):
        """Execute a scheduled activity."""
        try:
            activity = ScheduledActivity.query.get(activity_id)
            if not activity:
                return
            
            # Execute the action
            result = self.execute_action(activity.action_data)
            
            # Update activity
            activity.last_executed = datetime.utcnow()
            if activity.recurrence:
                activity.next_execution = datetime.utcnow() + timedelta(days=1)
            
            db.session.commit()
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing scheduled activity: {str(e)}")
    
    def _generate_report(self, action_data):
        """Generate a report from accumulated data."""
        try:
            report_data = action_data.get('report')
            
            report = Report(
                id=str(uuid.uuid4()),
                title=report_data.get('title'),
                description=report_data.get('description'),
                report_type=report_data.get('type', 'summary'),
                data=report_data.get('data', {}),
                action_ids=report_data.get('action_ids', [])
            )
            
            db.session.add(report)
            db.session.commit()
            
            return {
                'report_id': report.id,
                'title': report.title,
                'type': report.report_type
            }
        
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    def _execute_display_data(self, action_data):
        """Execute a display-style data action (runs query and formats output).

        Supports formats: 'table' (default), 'csv'/'excel', 'chart', 'paragraph',
        'summarized_text', 'pdf'/'word'/'pptx' (placeholders).
        """
        try:
            # Accept SQL same as database query
            query = action_data.get('sql_query') or action_data.get('query')
            if not query:
                raise ValueError("Query is required for DISPLAY_DATA")

            query = query.strip().strip('`')
            logger.info(f"→ Executing display data query: {query[:120]}...")
            rows = self.db_connector.execute_query(action_data.get('database', 'default'), query)

            # Serialize rows
            serializable_rows = []
            for row in rows:
                if isinstance(row, dict):
                    r = {}
                    for k, v in row.items():
                        if hasattr(v, 'isoformat'):
                            r[k] = v.isoformat()
                        else:
                            r[k] = v
                    serializable_rows.append(r)
                else:
                    serializable_rows.append(row)

            # Determine requested format
            fmt = action_data.get('format')
            if not fmt:
                # Try parse from parameters
                params = action_data.get('parameters')
                parsed = self._parse_parameters(params) if params else {}
                fmt = parsed.get('format') or parsed.get('display_format')

            fmt = (fmt or 'table').lower()

            # Generate a formatted summary using existing formatter
            formatted = self.result_formatter.format_result({'rows': serializable_rows, 'row_count': len(serializable_rows)}, 'DATABASE_QUERY')

            if fmt in ('table', 'datatable'):
                formatted['display_format'] = 'datatable'
                formatted['rows'] = serializable_rows
                return formatted

            if fmt in ('csv', 'excel'):
                # Generate CSV and return as base64 payload so frontend can download
                output = io.StringIO()
                if serializable_rows:
                    writer = csv.DictWriter(output, fieldnames=list(serializable_rows[0].keys()))
                    writer.writeheader()
                    for r in serializable_rows:
                        writer.writerow({k: ('' if v is None else v) for k, v in r.items()})
                csv_bytes = output.getvalue().encode('utf-8')
                b64 = base64.b64encode(csv_bytes).decode('ascii')
                return {
                    'status': 'success',
                    'display_format': 'csv',
                    'file_name': action_data.get('file_name') or 'result.csv',
                    'file_base64': b64,
                    'summary_levels': formatted.get('summary_levels', {}),
                    'row_count': len(serializable_rows)
                }

            if fmt == 'chart':
                # Create a simple chart spec: pick first numeric column
                numeric_col = None
                for col in (list(serializable_rows[0].keys()) if serializable_rows else []):
                    if all(isinstance(r.get(col), (int, float)) for r in serializable_rows if r.get(col) is not None):
                        numeric_col = col
                        break

                if not numeric_col:
                    # No numeric column; fallback to table
                    formatted['display_format'] = 'datatable'
                    return formatted

                labels = [str(i+1) for i in range(len(serializable_rows))]
                data = [r.get(numeric_col) or 0 for r in serializable_rows]
                chart_spec = {
                    'type': action_data.get('chart_type', 'bar'),
                    'labels': labels,
                    'datasets': [{
                        'label': numeric_col,
                        'data': data
                    }]
                }
                return {
                    'status': 'success',
                    'display_format': 'chart',
                    'chart_spec': chart_spec,
                    'summary_levels': formatted.get('summary_levels', {}),
                    'row_count': len(serializable_rows)
                }

            if fmt in ('paragraph', 'text', 'summarized_text'):
                # Provide a textual summary at requested detail level
                level = int(action_data.get('detail_level', 1)) if action_data.get('detail_level') else 1
                text = self.result_formatter.get_summary_by_level(formatted, level)
                return {
                    'status': 'success',
                    'display_format': 'text',
                    'text': text,
                    'summary_levels': formatted.get('summary_levels', {}),
                    'row_count': len(serializable_rows)
                }

            # For other formats (pdf/word/pptx) return summarized result and indicate not-implemented file conversion
            if fmt in ('pdf', 'word', 'pptx'):
                return {
                    'status': 'success',
                    'display_format': fmt,
                    'message': f"Requested format '{fmt}' is supported as an export target but server-side generation is not enabled. Returning summarized content.",
                    'summary_levels': formatted.get('summary_levels', {}),
                    'rows_preview': serializable_rows[:10],
                    'row_count': len(serializable_rows)
                }

            # Default fallback
            formatted['display_format'] = 'datatable'
            formatted['rows'] = serializable_rows
            return formatted

        except Exception as e:
            logger.error(f"Error executing display data action: {str(e)}")
            raise

    def _execute_procedural_plan(self, action_data, conversation_id=None):
        """Execute a procedural plan consisting of multiple steps.

        Each step is an action_data dict. We execute them sequentially and
        collect results. Nested action histories will be created by calls to
        execute_action for each step.
        """
        try:
            steps = action_data.get('steps') or []
            if not isinstance(steps, list) or len(steps) == 0:
                raise ValueError('PROCEDURAL_PLAN requires a non-empty "steps" list')

            aggregate = {'steps': [], 'status': 'success'}
            for idx, step in enumerate(steps):
                try:
                    # Each step should be a dict with type and parameters
                    step_type = step.get('type') if isinstance(step, dict) else None
                    if not step_type:
                        raise ValueError(f'Step {idx+1} missing type')

                    # Execute step by calling execute_action recursively
                    res = self.execute_action(step, conversation_id=conversation_id)
                    aggregate['steps'].append({'step': idx+1, 'type': step_type, 'result': res})
                except Exception as se:
                    aggregate['steps'].append({'step': idx+1, 'type': step.get('type') if isinstance(step, dict) else None, 'error': str(se)})
                    # Mark overall status failed but continue executing remaining steps
                    aggregate['status'] = 'partial_failure'

            return aggregate

        except Exception as e:
            logger.error(f"Error executing procedural plan: {str(e)}")
            raise
    
    def get_scheduled_activities(self):
        """Get all scheduled activities."""
        try:
            activities = ScheduledActivity.query.all()
            return [a.to_dict() for a in activities]
        except Exception as e:
            logger.error(f"Error getting scheduled activities: {str(e)}")
            return []
    
    def schedule_activity(self, activity_data):
        """Schedule an activity."""
        return self._execute_schedule({'activity': activity_data})
    
    def update_scheduled_activity(self, activity_id, activity_data):
        """Update a scheduled activity."""
        try:
            activity = ScheduledActivity.query.get(activity_id)
            if not activity:
                raise ValueError("Activity not found")
            
            for key, value in activity_data.items():
                if hasattr(activity, key):
                    setattr(activity, key, value)
            
            db.session.commit()
            return activity.to_dict()
        except Exception as e:
            logger.error(f"Error updating scheduled activity: {str(e)}")
            raise
    
    def delete_scheduled_activity(self, activity_id):
        """Delete a scheduled activity."""
        try:
            activity = ScheduledActivity.query.get(activity_id)
            if activity:
                db.session.delete(activity)
                db.session.commit()
                scheduler.remove_job(activity_id)
        except Exception as e:
            logger.error(f"Error deleting scheduled activity: {str(e)}")
            raise
    
    def get_reports(self):
        """Get all reports."""
        try:
            reports = Report.query.order_by(Report.created_at.desc()).all()
            return [r.to_dict() for r in reports]
        except Exception as e:
            logger.error(f"Error getting reports: {str(e)}")
            return []
    
    def get_report(self, report_id):
        """Get a specific report."""
        try:
            report = Report.query.get(report_id)
            return report.to_dict() if report else None
        except Exception as e:
            logger.error(f"Error getting report: {str(e)}")
            return None
    
    def delete_report(self, report_id):
        """Delete a report."""
        try:
            report = Report.query.get(report_id)
            if report:
                db.session.delete(report)
                db.session.commit()
        except Exception as e:
            logger.error(f"Error deleting report: {str(e)}")
            raise
    
    def generate_report(self, report_data):
        """Generate a new report."""
        return self._generate_report({'report': report_data})
