import { useRef, useState } from "react";
import { EntityIcon } from "./Icons";

const MAX_IMAGE_MB = 20;

/** Read a file as base64, without the "data:...;base64," prefix. */
const readAsBase64 = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload  = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

export default function SearchForm({ onSearch, isLoading, onReset, onImageChosen }) {
  const [name,         setName]        = useState("");
  const [username,     setUsername]    = useState("");
  const [email,        setEmail]       = useState("");
  const [linkedinUrl,  setLinkedinUrl] = useState("");
  const [imageFile,    setImageFile]   = useState(null);
  const [imageError,   setImageError]  = useState("");
  const imageInput = useRef(null);

  const clearImage = () => {
    setImageFile(null);
    if (imageInput.current) imageInput.current.value = "";
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    setImageError("");
    if (file && file.size > MAX_IMAGE_MB * 1024 * 1024) {
      clearImage();
      setImageError(`Choose an image under ${MAX_IMAGE_MB} MB.`);
      return;
    }
    setImageFile(file || null);
    if (file) onImageChosen();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    let image = null;
    if (imageFile) {
      try {
        image = { filename: imageFile.name, data: await readAsBase64(imageFile) };
      } catch {
        setImageError("Couldn't read that file. Choose it again.");
        return;
      }
    }

    onSearch({
      name:         name.trim(),
      username:     username.trim(),
      email:        email.trim(),
      linkedin_url: linkedinUrl.trim(),
      image,
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

      <div className="palette-entity">
        <EntityIcon name="image" size={26} />
        <div className="palette-entity-text">
          <label className="palette-entity-name" htmlFor="target-image">Image to analyze</label>
          <input
            id="target-image"
            ref={imageInput}
            type="file"
            className="input-field image-input"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleImageChange}
            disabled={locked}
          />
          {imageFile && !locked && (
            <button type="button" className="link-btn" onClick={clearImage}>Remove image</button>
          )}
          {imageError && <span className="field-error" role="alert">{imageError}</span>}
        </div>
      </div>

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
