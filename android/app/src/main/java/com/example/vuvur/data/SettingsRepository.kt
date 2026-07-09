package com.example.vuvur.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore // Import preferencesDataStore
import com.example.vuvur.data.OfflineMediaItem
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers // Import Dispatchers
import kotlinx.coroutines.SupervisorJob // Import SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch


// Define CoroutineScope and DataStore at the top level
private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
val Context.dataStore: DataStore<Preferences> by preferencesDataStore(
    name = "settings",
    scope = applicationScope
)

class SettingsRepository(
    private val dataStore: DataStore<Preferences>,
    private val scope: CoroutineScope // Scope passed from Application
) {

    private object PreferencesKeys {
        val ACTIVE_API_URL = stringPreferencesKey("active_api_url")
        val API_LIST = stringSetPreferencesKey("api_list")
        val ZOOM_LEVEL = floatPreferencesKey("zoom_level")
        val PASSCODE = stringPreferencesKey("passcode")
        val OFFLINE_STORAGE_LIMIT_GB = floatPreferencesKey("offline_storage_limit_gb")
        val OFFLINE_INDEX = stringPreferencesKey("offline_index")
        val OFFLINE_CACHE_MODE = stringPreferencesKey("offline_cache_mode")
    }

    // Use a default list relevant to your setup or common defaults
    private val DEFAULT_API_LIST = listOf(
        // below is home
        "http://100.70.215.39:3602",
        "http://100.70.215.39:3532",
        // below is azure hosted
        "http://100.108.234.82:3532"
    )

    // ✅ Map of default API URLs to their respective keys
    private val DEFAULT_API_KEYS = mapOf(
        // below is home
        "http://100.70.215.39:3602" to "vuvur_dev",
        "http://100.70.215.39:3532" to "vuvur_prod",
        // below is cloud hosted
        "http://100.108.234.82:3532" to "vuvur_prod"
    )

    // ✅ Map of API URLs to pretty aliases for UI
    private val DEFAULT_API_ALIASES = mapOf(
        "http://100.70.215.39:3602" to "home-dev",
        "http://100.70.215.39:3532" to "home-prod",
        "http://100.108.234.82:3532" to "doub-prod"
    )

    val activeApiUrlFlow: Flow<String> = dataStore.data.map { preferences ->
        preferences[PreferencesKeys.ACTIVE_API_URL] ?: DEFAULT_API_LIST.first()
    }

    val apiListFlow: Flow<List<String>> = dataStore.data.map { preferences ->
        preferences[PreferencesKeys.API_LIST]?.toList()?.takeIf { it.isNotEmpty() } ?: DEFAULT_API_LIST
    }

    val zoomLevelFlow: Flow<Float> = dataStore.data.map { preferences ->
        preferences[PreferencesKeys.ZOOM_LEVEL] ?: 2.5f
    }

    val passcodeFlow: Flow<String?> = dataStore.data.map { preferences ->
        preferences[PreferencesKeys.PASSCODE]
    }

    // --- Offline storage ---
    private val gson = Gson()
    private val offlineItemListType = object : TypeToken<List<OfflineMediaItem>>() {}.type

    val offlineStorageLimitGbFlow: Flow<Float> = dataStore.data.map { preferences ->
        preferences[PreferencesKeys.OFFLINE_STORAGE_LIMIT_GB] ?: 2.0f
    }

    val offlineIndexFlow: Flow<List<OfflineMediaItem>> = dataStore.data.map { preferences ->
        val json = preferences[PreferencesKeys.OFFLINE_INDEX]
        if (json.isNullOrEmpty()) emptyList()
        else gson.fromJson(json, offlineItemListType) ?: emptyList()
    }

    val offlineCacheModeFlow: Flow<String> = dataStore.data.map { preferences ->
        preferences[PreferencesKeys.OFFLINE_CACHE_MODE] ?: "ON_VIEW"
    }

    private val _refreshTrigger = MutableSharedFlow<Unit>(replay = 1)
    val refreshTrigger = _refreshTrigger.asSharedFlow()

    private val _apiChanged = MutableSharedFlow<String>()
    val apiChanged = _apiChanged.asSharedFlow()

    private val _zoomChanged = MutableSharedFlow<Float>()
    val zoomChanged = _zoomChanged.asSharedFlow()

    // Function to get the initial/current API URL (suspend function)
    // Used by VuvurApplication during initialization
    suspend fun getActiveApiUrl(): String {
        return activeApiUrlFlow.first() // Get the first value from the flow
    }

    // ✅ Public function to get the API key for a given URL
    suspend fun getApiKeyForUrl(url: String): String? {
        // In the future, this could check saved preferences.
        // For now, it only checks the hardcoded default map.
        return DEFAULT_API_KEYS[url]
    }

    // ✅ Public function to get the alias for a given URL
    fun getAliasForUrl(url: String): String {
        return DEFAULT_API_ALIASES[url] ?: url
    }

    suspend fun saveApiUrl(url: String) {
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.ACTIVE_API_URL] = url
        }
        _apiChanged.emit(url)
        _refreshTrigger.tryEmit(Unit)
    }

    suspend fun saveZoomLevel(level: Float) {
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.ZOOM_LEVEL] = level
        }
        _zoomChanged.emit(level)
    }

    suspend fun savePasscode(passcode: String) {
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.PASSCODE] = passcode
        }
    }

    suspend fun addApiUrlToList(url: String) {
        dataStore.edit { preferences ->
            val currentList = preferences[PreferencesKeys.API_LIST]?.toMutableSet() ?: mutableSetOf()
            currentList.add(url)
            preferences[PreferencesKeys.API_LIST] = currentList
        }
    }

    suspend fun triggerRefresh() {
        _refreshTrigger.emit(Unit)
    }

    suspend fun saveOfflineStorageLimitGb(gb: Float) {
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.OFFLINE_STORAGE_LIMIT_GB] = gb
        }
    }

    suspend fun saveOfflineCacheMode(mode: String) {
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.OFFLINE_CACHE_MODE] = mode
        }
    }

    suspend fun saveOfflineIndex(items: List<OfflineMediaItem>) {
        val json = gson.toJson(items)
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.OFFLINE_INDEX] = json
        }
    }

    suspend fun getOfflineIndex(): List<OfflineMediaItem> {
        return offlineIndexFlow.first()
    }
}
