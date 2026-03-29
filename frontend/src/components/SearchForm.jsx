import React, { useState } from 'react';

const SearchForm = ({ onSearch, isLoading }) => {
  const [targetName, setTargetName] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (targetName.trim()) {
      onSearch(targetName);
    }
  };

  return (
    <div className="search-section">
      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          placeholder="Search target..."
          value={targetName}
          onChange={(e) => setTargetName(e.target.value)}
          className="input-field"
          disabled={isLoading}
        />
        <button type="submit" className="search-btn" disabled={isLoading || !targetName.trim()}>
          {isLoading ? '...' : 'EXECUTE'}
        </button>
      </form>
    </div>
  );
};

export default SearchForm;
