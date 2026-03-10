import React, { useState } from 'react'
import { FiArrowLeft } from 'react-icons/fi'
import DatabaseSettings from './settings/DatabaseSettings'
import LLMSettings from './settings/LLMSettings'
import RAGSettings from './settings/RAGSettings'
import SystemSettings from './settings/SystemSettings'
import DataIngestionSettings from './settings/DataIngestionSettings'
import ScheduledActivities from './settings/ScheduledActivities'
import DataSourcesAndAPIsSettings from './settings/DataSourcesAndAPIsSettings'
import DBMSExplorer from './DBMSExplorer'
import ReportsSettings from './settings/ReportsSettings'
import OtherSettings from './settings/OtherSettings'

interface SettingsViewProps {
  onBack: () => void
}

export default function SettingsView({ onBack }: SettingsViewProps) {
  const [activeTab, setActiveTab] = useState(0)

  // Configuration: Set tabs to hide by adding their labels to this array
  // To re-enable a tab later, simply remove it from this array
  const HIDDEN_TABS = [
    'Scheduled Tasks',
    'Data Sources & APIs',
    'DBMS',
    'Reports',
    'Other'
  ]

  const allTabs = [
    { label: 'Database', component: DatabaseSettings },
    { label: 'Data Ingestion', component: DataIngestionSettings },
    { label: 'LLM Models', component: LLMSettings },
    { label: 'RAG', component: RAGSettings },
    { label: 'System', component: SystemSettings },
    { label: 'Scheduled Tasks', component: ScheduledActivities },
    { label: 'Data Sources & APIs', component: DataSourcesAndAPIsSettings },
    { label: 'DBMS', component: DBMSExplorer },
    { label: 'Reports', component: ReportsSettings },
    { label: 'Other', component: OtherSettings },
  ]

  // Filter out hidden tabs
  const tabs = allTabs.filter(tab => !HIDDEN_TABS.includes(tab.label))

  const ActiveComponent = tabs[activeTab]?.component

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h2>Settings</h2>
        <button className="btn-secondary" onClick={onBack}>
          <FiArrowLeft style={{ marginRight: '0.5rem' }} />
          Back to Chat
        </button>
      </div>

      <div className="settings-tabs">
        {tabs.map((tab, index) => (
          <button
            key={index}
            className={`settings-tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="settings-content">
        <div className="settings-panel">
          <ActiveComponent />
        </div>
      </div>
    </div>
  )
}
