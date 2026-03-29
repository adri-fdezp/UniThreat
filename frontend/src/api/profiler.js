const API_BASE_URL = 'http://localhost:5000/api';

/**
 * Fetches the risk profile for a given target name and specific modules.
 * @param {string} targetName 
 * @param {Array} modules - e.g., ['social', 'docs']
 * @returns {Promise<Object>} The profile data.
 */
export const getRiskProfile = async (targetName, modules = []) => {
  const response = await fetch(`${API_BASE_URL}/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      name: targetName,
      modules: modules
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || `Server responded with ${response.status}`);
  }

  return response.json();
};