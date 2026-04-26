import { useState } from "react";

export default function SearchForm({ onSearch, isLoading, onReset }) {
  const [name,     setName]     = useState("");
  const [username, setUsername] = useState("");
  const [email,    setEmail]    = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSearch({ name: name.trim(), username: username.trim(), email: email.trim() });
  };

  const locked = isLoading || !!onReset;

  return (
    <form onSubmit={handleSubmit} className="search-form">
      <input
        type="text"
        className="input-field"
        placeholder="Full name *"
        value={name}
        onChange={(e) => setName(e.target.value)}
        disabled={locked}
        required
      />
      <input
        type="text"
        className="input-field"
        placeholder="@username / handle (optional)"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        disabled={locked}
      />
      <input
        type="email"
        className="input-field"
        placeholder="email@example.com (optional)"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={locked}
      />

      {onReset ? (
        <button type="button" className="reset-btn" onClick={onReset}>
          ← NEW SEARCH
        </button>
      ) : (
        <button
          type="submit"
          className="execute-btn"
          disabled={isLoading || !name.trim()}
        >
          {isLoading ? "GATHERING…" : "EXECUTE"}
        </button>
      )}
    </form>
  );
}
