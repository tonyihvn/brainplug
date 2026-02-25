import React, { useState, useEffect } from 'react'
import { ScheduledActivity } from '../../types'
import { apiClient } from '../../services/geminiService'
import { showConfirm, showLoading, closeSwal, showAlert } from '../swal'

export default function ScheduledActivities() {
  const [activities, setActivities] = useState<ScheduledActivity[]>([])
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    loadActivities()
  }, [])

  const loadActivities = async () => {
    try {
      const response = await apiClient.getScheduledActivities()
      setActivities(response.data.data || [])
    } catch (error) {
      console.error('Error loading scheduled activities:', error)
    }
  }

  const handleDelete = async (id: string) => {
    const ok = await showConfirm('Delete this activity?', 'Are you sure you want to delete this scheduled activity?')
    if (!ok) return
    try {
      showLoading('Deleting...')
      await apiClient.deleteScheduledActivity(id)
      await loadActivities()
    } catch (error) {
      console.error('Error deleting activity:', error)
      showAlert('Error', 'Error deleting activity', 'error')
    } finally {
      closeSwal()
    }
  }

  const handleToggle = async (activity: ScheduledActivity) => {
    try {
      await apiClient.updateScheduledActivity(activity.id, {
        ...activity,
        is_active: !activity.is_active,
      })
      await loadActivities()
    } catch (error) {
      console.error('Error updating activity:', error)
    }
  }

  return (
    <div>
      <h3>Scheduled Activities & Reports</h3>
      <p style={{ marginBottom: '1.5rem', color: '#718096' }}>
        View and manage activities scheduled for automatic execution.
      </p>

      <button className="btn-add" onClick={() => setShowForm(!showForm)}>
        + Schedule New Activity
      </button>

      {activities.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">⏱️</div>
          <div className="empty-state-text">No scheduled activities yet</div>
          <p>Activities are created from conversations when you confirm actions with a schedule.</p>
        </div>
      ) : (
        <table className="table" style={{ marginTop: '1.5rem' }}>
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Scheduled For</th>
              <th>Recurrence</th>
              <th>Status</th>
              <th>Last Executed</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {activities.map(activity => (
              <tr key={activity.id}>
                <td>{activity.title}</td>
                <td>{activity.action_type}</td>
                <td>{new Date(activity.scheduled_for).toLocaleDateString()}</td>
                <td>{activity.recurrence || 'Once'}</td>
                <td>
                  <button
                    onClick={() => handleToggle(activity)}
                    style={{
                      padding: '0.25rem 0.75rem',
                      background: activity.is_active ? '#48bb78' : '#cbd5e0',
                      color: activity.is_active ? 'white' : '#2d3748',
                      border: 'none',
                      borderRadius: '0.25rem',
                      cursor: 'pointer',
                    }}
                  >
                    {activity.is_active ? '✓ Active' : 'Inactive'}
                  </button>
                </td>
                <td>{activity.last_executed ? new Date(activity.last_executed).toLocaleString() : '-'}</td>
                <td>
                  <button className="btn-delete" onClick={() => handleDelete(activity.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
