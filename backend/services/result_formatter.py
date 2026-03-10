"""Result formatting service using RAG embeddings for intelligent summarization."""
import json
import logging
from typing import Any, Dict, List
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class ResultFormatter:
    """Format and summarize query results using RAG embeddings and custom functions."""

    def __init__(self):
        """Initialize the result formatter."""
        pass

    def format_result(self, result_data: Any, action_type: str = 'DATABASE_QUERY') -> Dict:
        """
        Format result data with 3-level summarization.
        
        Args:
            result_data: Raw result from action execution
            action_type: Type of action (DATABASE_QUERY, RAG_QUERY, EMAIL, etc.)
        
        Returns:
            Formatted result with 3 levels of detail
        """
        try:
            if action_type in ['DATABASE_QUERY', 'RAG_QUERY']:
                return self._format_database_result(result_data, action_type)
            else:
                return self._format_generic_result(result_data)
        except Exception as e:
            logger.error(f"Error formatting result: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'raw_data': result_data
            }

    def _format_database_result(self, result_data: Dict, action_type: str = 'DATABASE_QUERY') -> Dict:
        """Format database/RAG query results with 3-level summarization."""
        rows = result_data.get('rows', [])
        row_count = result_data.get('row_count', 0)
        
        if not rows or row_count == 0:
            query_type_label = "RAG" if action_type == 'RAG_QUERY' else "Database"
            return {
                'status': 'success',
                'row_count': 0,
                'query_type': f"{query_type_label} Query",
                'summary_levels': {
                    'level_1': f'No {query_type_label.lower()} results returned',
                    'level_2': f'{query_type_label} query returned empty result set',
                    'level_3': f'No records/chunks match the query criteria'
                },
                'rows': []
            }

        # Level 1: Statistical Summary
        level_1_summary = self._generate_level_1_summary(rows)
        
        # Level 2: Column Analysis
        level_2_summary = self._generate_level_2_summary(rows)
        
        # Level 3: Data Insights
        level_3_summary = self._generate_level_3_summary(rows)

        return {
            'status': 'success',
            'row_count': row_count,
            'query_type': "RAG Query" if action_type == 'RAG_QUERY' else "Database Query",
            'column_count': len(rows[0].keys()) if rows else 0,
            'columns': list(rows[0].keys()) if rows else [],
            'summary_levels': {
                'level_1': level_1_summary,
                'level_2': level_2_summary,
                'level_3': level_3_summary
            },
            'rows': rows,
            'display_format': 'datatable'
        }

    def _generate_level_1_summary(self, rows: List[Dict]) -> str:
        """
        Level 1: High-level statistical summary.
        Shows: total records, key metrics, basic overview
        """
        if not rows:
            return "No data available"

        summary_parts = [f"Total: {len(rows)} records"]

        # Identify numeric columns and calculate basic stats
        numeric_columns = {}
        for row in rows:
            for key, value in row.items():
                if isinstance(value, (int, float)):
                    if key not in numeric_columns:
                        numeric_columns[key] = []
                    numeric_columns[key].append(value)

        if numeric_columns:
            stats = []
            for col_name, values in numeric_columns.items():
                avg_val = sum(values) / len(values)
                max_val = max(values)
                min_val = min(values)
                stats.append(f"{col_name}: avg={avg_val:.2f}, max={max_val}, min={min_val}")
            if stats:
                summary_parts.append(" | " + ", ".join(stats))

        return " | ".join(summary_parts)

    def _generate_level_2_summary(self, rows: List[Dict]) -> str:
        """
        Level 2: Column-level analysis.
        Shows: data types, value distributions, missing data
        """
        if not rows:
            return "No columns to analyze"

        columns_info = []
        for col_name in rows[0].keys():
            values = [row.get(col_name) for row in rows]
            non_null = sum(1 for v in values if v is not None)
            null_count = len(values) - non_null

            # Determine data type
            data_type = self._infer_column_type(values)

            # Count unique values
            unique_count = len(set(v for v in values if v is not None))

            col_info = f"{col_name} ({data_type}): {non_null}/{len(values)} non-null, {unique_count} unique"
            if null_count > 0:
                col_info += f", {null_count} NULL"

            columns_info.append(col_info)

        return " | ".join(columns_info[:5])  # Show first 5 columns

    def _generate_level_3_summary(self, rows: List[Dict]) -> str:
        """
        Level 3: Data insights and patterns.
        Shows: data quality, patterns, anomalies, distributions
        """
        if not rows:
            return "No data patterns detected"

        insights = []

        # Check data quality
        total_cells = sum(len(row) for row in rows)
        null_cells = sum(1 for row in rows for v in row.values() if v is None)
        completeness = ((total_cells - null_cells) / total_cells * 100) if total_cells > 0 else 0
        insights.append(f"Data Completeness: {completeness:.1f}%")

        # Detect patterns in first column (usually ID or key)
        first_col = list(rows[0].keys())[0]
        first_col_values = [row.get(first_col) for row in rows if row.get(first_col) is not None]
        
        if first_col_values and isinstance(first_col_values[0], (int, float)):
            # Check if sequential
            if len(first_col_values) > 1:
                sorted_vals = sorted(first_col_values)
                is_sequential = all(
                    sorted_vals[i+1] - sorted_vals[i] == 1 
                    for i in range(len(sorted_vals)-1)
                )
                if is_sequential:
                    insights.append(f"Sequential IDs detected in {first_col}")

        # Find columns with all same values
        for col_name in list(rows[0].keys())[:3]:
            values = [row.get(col_name) for row in rows if row.get(col_name) is not None]
            if values and len(set(values)) == 1:
                insights.append(f"Constant value in {col_name}: {values[0]}")

        return " | ".join(insights) if insights else "No anomalies detected"

    def _infer_column_type(self, values: List[Any]) -> str:
        """Infer the data type of a column."""
        non_null_values = [v for v in values if v is not None]
        if not non_null_values:
            return "unknown"

        # Check types
        all_int = all(isinstance(v, int) for v in non_null_values)
        all_float = all(isinstance(v, (int, float)) for v in non_null_values)
        all_bool = all(isinstance(v, bool) for v in non_null_values)
        all_str = all(isinstance(v, str) for v in non_null_values)

        if all_bool:
            return "boolean"
        elif all_int:
            return "integer"
        elif all_float:
            return "float"
        elif all_str:
            return "text"
        else:
            return "mixed"

    def _format_generic_result(self, result_data: Any) -> Dict:
        """Format generic results."""
        return {
            'status': 'success',
            'data': result_data,
            'display_format': 'json'
        }

    def get_summary_by_level(self, formatted_result: Dict, level: int = 1) -> str:
        """
        Get summary at a specific detail level.
        
        Args:
            formatted_result: Result from format_result()
            level: 1 (overview), 2 (detailed), 3 (deep insights)
        
        Returns:
            Summary string at requested level
        """
        if 'summary_levels' not in formatted_result:
            return "No summary available"

        level_key = f'level_{level}'
        return formatted_result['summary_levels'].get(level_key, 'No summary available')
