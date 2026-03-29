import React, { useMemo } from 'react';
import PropTypes from 'prop-types';

const ProfileResults = ({ profileData }) => {
  if (!profileData) return (
    <div className="empty-state">READY FOR TARGET DATA INGESTION</div>
  );

  // Memoize the flattened and sorted results to improve performance
  const processedResults = useMemo(() => {
    let allResults = [];
    
    // Flatten the grouped sources into a single list
    if (profileData.sources) {
      Object.entries(profileData.sources).forEach(([sourceName, results]) => {
        if (Array.isArray(results)) {
          results.forEach(item => {
            allResults.push({ ...item, source: sourceName });
          });
        }
      });
    }

    return allResults;
  }, [profileData]);

  return (
    <div className="dashboard-grid">
      {processedResults.map((item, index) => (
        <div key={`${item.url}-${index}`} className="data-card">
          <div className="card-header">
            <span>{item.source.split(':')[1]?.trim() || item.source}</span>
          </div>
          <div className="card-content-wrapper">
            {item.image && <img src={item.image} alt="" className="profile-thumb" />}
            <div className="card-text">
              <a href={item.url} target="_blank" rel="noopener noreferrer" className="card-title">
                {item.title}
              </a>
              <p className="card-body">{item.description}</p>
            </div>
          </div>
          <div className="card-footer" title={item.url}>{item.url}</div>
        </div>
      ))}
    </div>
  );
};

ProfileResults.propTypes = {
  profileData: PropTypes.shape({
    sources: PropTypes.object
  })
};

export default ProfileResults;