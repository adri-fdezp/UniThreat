import { useState } from "react";
import { EntityIcon } from "./Icons";

export default function SearchForm({ onSearch, isLoading, onReset }) {
  const [name,         setName]        = useState("");
  const [username,     setUsername]    = useState("");
  const [email,        setEmail]       = useState("");
  const [linkedinUrl,  setLinkedinUrl] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSearch({
      name:         name.trim(),
      username:     username.trim(),
      email:        email.trim(),
      linkedin_url: linkedinUrl.trim(),
    });
  };

  const locked = isLoading || !!onReset;

  // Each target field is labelled with the entity it becomes on the graph
  const fields = [
    { icon: "person",  label: "Person",       type: "text",  value: name,        set: setName,        placeholder: "Full name", required: true },
    { icon: "alias",   label: "Alias",        type: "text",  value: username,    set: setUsername,    placeholder: "Username or handle" },
    { icon: "email",   label: "Email",        type: "email", value: email,       set: setEmail,       placeholder: "name@example.com" },
    { icon: "website", label: "LinkedIn URL", type: "url",   value: linkedinUrl, set: setLinkedinUrl, placeholder: "https://linkedin.com/in/…" },
  ];

  return (
    <form id="target-form" onSubmit={handleSubmit} className="search-form">
      {fields.map((f) => (
        <label key={f.label} className="palette-entity">
          <EntityIcon name={f.icon} size={26} />
          <span className="palette-entity-text">
            <span className="palette-entity-name">
              {f.label}{f.required && <span className="required-mark" aria-hidden="true"> *</span>}
            </span>
            <input
              type={f.type}
              className="input-field"
              placeholder={f.placeholder}
              value={f.value}
              onChange={(e) => f.set(e.target.value)}
              disabled={locked}
              required={f.required}
            />
          </span>
        </label>
      ))}

      {onReset ? (
        <button type="button" className="reset-btn" onClick={onReset}>
          New graph
        </button>
      ) : (
        <button
          type="submit"
          className="execute-btn"
          disabled={isLoading || !name.trim()}
        >
          {isLoading ? "Running…" : "Run analysis"}
        </button>
      )}
    </form>
  );
}
