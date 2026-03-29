import { useState } from 'react';
import { getRiskProfile } from './api/profiler';
import Header from './components/Header';
import SearchForm from './components/SearchForm';
import ProfileResults from './components/ProfileResults';
import './styles/App.css';

const MODULES = [
  { id: 'google', label: 'GOOGLE' }
];

function App() {
  const [profileData, setProfileData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedModules, setSelectedModules] = useState(['google']);

  const handleSearch = async (targetName) => {
    if (selectedModules.length === 0) return setError("Select at least one module.");
    
    setIsLoading(true);
    setError(null);
    setProfileData(null);

    try {
      const data = await getRiskProfile(targetName, selectedModules);
      setProfileData(data);
    } catch (err) {
      setError(err.message || "Search failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleModule = (id) => {
    setSelectedModules(prev => 
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    );
  };

  return (
    <div className="app-container">
      <Header />
      
      <div className="workspace">
        {/* SIDEBAR: Configuration */}
        <aside className="sidebar">
          <section className="side-section">
            <label className="section-label">IDENTIFIER</label>
            <SearchForm onSearch={handleSearch} isLoading={isLoading} />
          </section>

          <section className="side-section">
            <label className="section-label">MODULES</label>
            <div className="module-grid">
              {MODULES.map(mod => (
                <button
                  key={mod.id}
                  className={`mod-toggle ${selectedModules.includes(mod.id) ? 'active' : ''}`}
                  onClick={() => toggleModule(mod.id)}
                  disabled={isLoading}
                >
                  {mod.label}
                </button>
              ))}
            </div>
          </section>

          <section className="side-section status-area">
            <label className="section-label">STATUS</label>
            <div className={`status-indicator ${isLoading ? 'loading' : ''}`}>
              {isLoading ? 'SCANNING...' : profileData ? 'COMPLETE' : 'READY'}
            </div>
          </section>
        </aside>

        {/* MAIN: Results */}
        <main className="main-content">
          {profileData && (
            <div className="results-toolbar">
              <span className="hit-count">{Object.values(profileData.sources).flat().length} HITS</span>
            </div>
          )}
          
          {error && <div className="error-banner">{error}</div>}
          
          <ProfileResults profileData={profileData} />
        </main>
      </div>
    </div>
  );
}

export default App;