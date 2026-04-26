import React, { useState } from 'react';

const InvestigationNotes = () => {
  const [notes, setNotes] = useState('');

  const handleChange = (e) => {
    setNotes(e.target.value);
  };

  return (
    <aside className="notes-sidebar">
      <section className="side-section" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <label className="section-label">INVESTIGATION NOTES</label>
        <textarea
          className="notes-textarea"
          placeholder="Paste relevant information, links, or findings here..."
          value={notes}
          onChange={handleChange}
        />
      </section>
    </aside>
  );
};

export default InvestigationNotes;
