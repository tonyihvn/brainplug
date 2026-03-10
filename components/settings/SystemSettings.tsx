import React, { useState, useEffect } from 'react'
import { apiClient } from '../../services/geminiService'

interface RestrictedKeywords {
  DROP: boolean
  DELETE: boolean
  INSERT: boolean
  ALTER: boolean
  SELECT: boolean
  UPDATE: boolean
  TRUNCATE: boolean
}

export default function SystemSettings() {
  const [smtp, setSmtp] = useState({ host: '', port: '', username: '', password: '' })
  const [imap, setImap] = useState({ host: '', port: '', username: '', password: '' })
  const [pop, setPop] = useState({ host: '', port: '', username: '', password: '' })
  const [restrictedKeywords, setRestrictedKeywords] = useState<RestrictedKeywords>({
    DROP: true,
    DELETE: true,
    INSERT: true,
    ALTER: true,
    SELECT: false,
    UPDATE: true,
    TRUNCATE: true
  })
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
      if (data.restricted_keywords) {
        setRestrictedKeywords(data.restricted_keywords)
      }
    } catch (error) {
      console.error('Error loading system settings:', error)
    }
  }

  const handleSaveAll = async () => {
    try {
      const resp = await apiClient.updateSystemSettings({ 
        smtp, 
        imap, 
        pop,
        restricted_keywords: restrictedKeywords
      })
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

      <div style={{ marginTop: '2rem', padding: '1.5rem', backgroundColor: '#fff5f5', borderRadius: '0.5rem', borderLeft: '4px solid #fc8181' }}>
        <h4 style={{ marginBottom: '1rem' }}>SQL Query Security</h4>
        <p style={{ color: '#742a2a', marginBottom: '1rem', fontSize: '0.95rem' }}>
          Restrict SQL keywords in extraction queries and LLM actions to prevent unauthorized database modifications.
          Selected keywords will be blocked at both client and server level.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
          {Object.keys(restrictedKeywords).map((keyword) => (
            <label key={keyword} style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', userSelect: 'none' }}>
              <input 
                type="checkbox"
                checked={restrictedKeywords[keyword as keyof RestrictedKeywords]}
                onChange={(e) => setRestrictedKeywords(prev => ({
                  ...prev,
                  [keyword]: e.target.checked
                }))}
                style={{ marginRight: '0.5rem', cursor: 'pointer' }}
              />
              <span style={{ fontFamily: 'monospace', fontWeight: '500' }}>{keyword}</span>
            </label>
          ))}
        </div>
        <small style={{ color: '#742a2a', display: 'block', marginTop: '1rem' }}>
          When enabled, these keywords will be prevented from running in extraction queries and prevented from being used in LLM-suggested actions.
        </small>
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
