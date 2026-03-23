/* global API, Toast, Cache */

/**
 * API Helper Utilities
 *
 * Reduces duplication in CRUD operations with standard error handling,
 * cache invalidation, and success messages.
 */

/**
 * Perform a CRUD operation with standard error handling.
 *
 * @param {Object} options - Operation options
 * @param {string} options.method - HTTP method ('get', 'post', 'put', 'patch', 'delete')
 * @param {string} options.endpoint - API endpoint
 * @param {Object} [options.payload] - Request payload (for POST/PUT/PATCH)
 * @param {string|RegExp} [options.cachePattern] - Cache pattern to invalidate after mutation
 * @param {string} [options.successMsg] - Success message to show
 * @param {string} [options.errorMsg] - Error message prefix
 * @param {Function} [options.onSuccess] - Callback after successful operation
 * @param {Function} [options.onError] - Callback after error
 * @returns {Promise<any>} API response data
 */
async function apiRequest(options) {
  const {
    method,
    endpoint,
    payload,
    cachePattern,
    successMsg,
    errorMsg = 'Fout',
    onSuccess,
    onError
  } = options;

  try {
    let result;

    switch (method.toLowerCase()) {
      case 'get':
        result = await API.get(endpoint);
        break;
      case 'post':
        result = await API.post(endpoint, payload);
        break;
      case 'put':
        result = await API.put(endpoint, payload);
        break;
      case 'patch':
        result = await API.patch(endpoint, payload);
        break;
      case 'delete':
        result = await API.delete(endpoint);
        break;
      default:
        throw new Error(`Unsupported method: ${method}`);
    }

    // Invalidate cache if pattern provided
    if (cachePattern && typeof Cache !== 'undefined') {
      Cache.invalidate(cachePattern);
    }

    // Show success message if provided
    if (successMsg) {
      Toast.show(successMsg, 'success');
    }

    // Call success callback
    if (onSuccess) {
      await onSuccess(result);
    }

    return result;
  } catch (err) {
    const message = err.detail || err.message || errorMsg;
    Toast.show(message, 'error');

    if (onError) {
      onError(err);
    }

    throw err;
  }
}

/**
 * Helper for creating an item (POST request).
 *
 * @param {string} endpoint - API endpoint
 * @param {Object} payload - Item data
 * @param {Object} [options] - Additional options (cachePattern, successMsg, onSuccess)
 * @returns {Promise<any>} Created item
 */
async function createItem(endpoint, payload, options = {}) {
  return apiRequest({
    method: 'post',
    endpoint,
    payload,
    successMsg: options.successMsg || 'Aangemaakt!',
    ...options
  });
}

/**
 * Helper for updating an item (PUT request).
 *
 * @param {string} endpoint - API endpoint (should include ID)
 * @param {Object} payload - Updated item data
 * @param {Object} [options] - Additional options (cachePattern, successMsg, onSuccess)
 * @returns {Promise<any>} Updated item
 */
async function updateItem(endpoint, payload, options = {}) {
  return apiRequest({
    method: 'put',
    endpoint,
    payload,
    successMsg: options.successMsg || 'Bijgewerkt!',
    ...options
  });
}

/**
 * Helper for deleting an item (DELETE request).
 *
 * @param {string} endpoint - API endpoint (should include ID)
 * @param {Object} [options] - Additional options (cachePattern, successMsg, onSuccess)
 * @returns {Promise<void>}
 */
async function deleteItem(endpoint, options = {}) {
  return apiRequest({
    method: 'delete',
    endpoint,
    successMsg: options.successMsg || 'Verwijderd',
    ...options
  });
}

/**
 * Helper for loading data with caching and error handling.
 *
 * @param {string} endpoint - API endpoint
 * @param {Object} [options] - Options
 * @param {string} [options.cacheKey] - Cache key (enables caching)
 * @param {number} [options.cacheTTL=60000] - Cache TTL in milliseconds
 * @param {boolean} [options.useCache=true] - Whether to use cache
 * @param {string} [options.errorMsg] - Error message to show on failure
 * @param {any} [options.fallback=[]] - Fallback value on error
 * @returns {Promise<any>} Loaded data
 */
async function loadData(endpoint, options = {}) {
  const {
    cacheKey,
    cacheTTL = 60000,
    useCache = true,
    errorMsg = 'Kon data niet laden',
    fallback = []
  } = options;

  // Try cache first if enabled
  if (cacheKey && useCache && typeof Cache !== 'undefined') {
    const cached = Cache.get(cacheKey);
    if (cached) {
      return cached;
    }
  }

  try {
    const data = await API.get(endpoint);

    // Cache if key provided
    if (cacheKey && typeof Cache !== 'undefined') {
      Cache.set(cacheKey, data, cacheTTL);
    }

    return data;
  } catch (err) {
    Toast.show(errorMsg, 'error');
    return fallback;
  }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
  window.APIHelpers = {
    apiRequest,
    createItem,
    updateItem,
    deleteItem,
    loadData
  };
}
