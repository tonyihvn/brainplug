import React, { useState, useEffect } from 'react'
import { apiClient } from '../../services/geminiService'

export default function SystemSettings() {
  const [smtp, setSmtp] = useState({ host: '', port: '', username: '', password: '' })
  const [imap, setImap] = useState({ host: '', port: '', username: '', password: '' })
  const [pop, setPop] = useState({ host: '', port: '', username: '', password: '' })
  const [envSaved, setEnvSaved] = useState<string[]>([])

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const response = await apiClient.getSystemSettings()
      const data = response.data.data
      if (data.smtp) setSmtp(data.smtp)
      if (data.imap) setImap(data.imap)
      if (data.pop) setPop(data.pop)
    } catch (error) {
      console.error('Error loading system settings:', error)
    }
  }

  const handleSaveAll = async () => {
    try {
      const resp = await apiClient.updateSystemSettings({ smtp, imap, pop })
      const saved = resp.data?.data?.env_saved || []
      setEnvSaved(saved)
      alert('System settings updated successfully')
    } catch (error) {
      console.error('Error saving system settings:', error)
      alert('Error saving settings')
    }
  }

  const handleInputChange = (section: string, field: string, value: string) => {
    if (section === 'smtp') setSmtp(prev => ({ ...prev, [field]: value }))
    else if (section === 'imap') setImap(prev => ({ ...prev, [field]: value }))
    else if (section === 'pop') setPop(prev => ({ ...prev, [field]: value }))
  }

  return (
    <div>
      <h3>System Settings</h3>
      <p style={{ marginBottom: '1.5rem', color: '#718096' }}>
        Configure email settings for sending and receiving emails.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* SMTP Settings */}
        <div>
          <h4>SMTP Settings (Email Sending)</h4>
          <div className="form-group">
            <label>Host</label>
            <input
              type="text"
              value={smtp.host}
              onChange={(e) => handleInputChange('smtp', 'host', e.target.value)}
              placeholder="smtp.gmail.com"
            />
          </div>
          <div className="form-group">
            <label>Port</label>
            <input
              type="number"
              value={smtp.port}
              onChange={(e) => handleInputChange('smtp', 'port', e.target.value)}
              placeholder="587"
            />
          </div>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={smtp.username}
              onChange={(e) => handleInputChange('smtp', 'username', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={smtp.password}
              onChange={(e) => handleInputChange('smtp', 'password', e.target.value)}
            />
            {envSaved.find(k => k.startsWith('SMTP_')) && (
              <div style={{ color: '#2f855a', fontSize: '0.875rem' }}>Saved to .env</div>
            )}
          </div>
        </div>

        {/* IMAP Settings */}
        <div>
          <h4>IMAP Settings (Email Reading)</h4>
          <div className="form-group">
            <label>Host</label>
            <input
              type="text"
              value={imap.host}
              onChange={(e) => handleInputChange('imap', 'host', e.target.value)}
              placeholder="imap.gmail.com"
            />
          </div>
          <div className="form-group">
            <label>Port</label>
            <input
              type="number"
              value={imap.port}
              onChange={(e) => handleInputChange('imap', 'port', e.target.value)}
              placeholder="993"
            />
          </div>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={imap.username}
              onChange={(e) => handleInputChange('imap', 'username', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={imap.password}
              onChange={(e) => handleInputChange('imap', 'password', e.target.value)}
            />
            {envSaved.find(k => k.startsWith('IMAP_')) && (
              <div style={{ color: '#2f855a', fontSize: '0.875rem' }}>Saved to .env</div>
            )}
          </div>
        </div>
      </div>

      <div style={{ marginTop: '2rem', padding: '1.5rem', backgroundColor: '#f7fafc', borderRadius: '0.5rem' }}>
        <h4>POP3 Settings (Alternative Email Reading)</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="form-group">
            <label>Host</label>
            <input
              type="text"
              value={pop.host}
              onChange={(e) => handleInputChange('pop', 'host', e.target.value)}
              placeholder="pop.gmail.com"
            />
          </div>
          <div className="form-group">
            <label>Port</label>
            <input
              type="number"
              value={pop.port}
              onChange={(e) => handleInputChange('pop', 'port', e.target.value)}
              placeholder="995"
            />
          </div>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={pop.username}
              onChange={(e) => handleInputChange('pop', 'username', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={pop.password}
              onChange={(e) => handleInputChange('pop', 'password', e.target.value)}
            />
            {envSaved.find(k => k.startsWith('POP_')) && (
              <div style={{ color: '#2f855a', fontSize: '0.875rem' }}>Saved to .env</div>
            )}
          </div>
        </div>
      </div>

      <div className="form-actions" style={{ marginTop: '2rem' }}>
        <button type="button" className="btn-save" onClick={handleSaveAll}>
          Save All Settings
        </button>
      </div>
    </div>
  )
}
