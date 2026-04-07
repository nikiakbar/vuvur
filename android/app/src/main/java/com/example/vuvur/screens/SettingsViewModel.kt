package com.example.vuvur.screens

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.vuvur.VuvurApplication
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch

data class SettingsUiState(
    val isLoading: Boolean = false,
    val activeApi: String = "",
    val apiList: List<String> = emptyList(),
    // ✅ Add map of URL to alias for the UI
    val apiAliases: Map<String, String> = emptyMap(),
    // ✅ Add zoomLevel to the UI state
    val zoomLevel: Float = 2.5f,
    val message: String? = null
)

class SettingsViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as VuvurApplication
    private val repository = app.settingsRepository
    private var apiService = app.vuvurApiService

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            // ✅ Combine all settings flows into one UI state
            combine(
                repository.activeApiUrlFlow,
                repository.apiListFlow,
                repository.zoomLevelFlow
            ) { activeUrl, urlList, zoom ->
                // ✅ Extract aliases for the list of URLs
                val aliases = urlList.associateWith { repository.getAliasForUrl(it) }
                SettingsUiState(
                    activeApi = activeUrl,
                    apiList = urlList,
                    apiAliases = aliases,
                    zoomLevel = zoom
                )
            }.collect {
                _uiState.value = it
            }
        }
        viewModelScope.launch {
            repository.apiChanged.collectLatest { newApiUrl ->
                // ✅ Get the key for the new URL
                val newApiKey = repository.getApiKeyForUrl(newApiUrl)
                // ✅ Pass both to createService
                apiService = app.apiClient.createService(newApiUrl, newApiKey)
            }
        }
    }

    fun saveSettings(newActiveApi: String) {
        viewModelScope.launch(Dispatchers.IO) {
            repository.saveApiUrl(newActiveApi)
            _uiState.value = _uiState.value.copy(message = "Settings saved!")
        }
    }

    // ✅ Add a function to save the zoom level
    fun saveZoomLevel(level: Float) {
        viewModelScope.launch(Dispatchers.IO) {
            repository.saveZoomLevel(level)
        }
    }

    fun runCacheCleanup() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val response = apiService.cleanCache()
                _uiState.value = _uiState.value.copy(message = response.message)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(message = "Cleanup failed")
            }
        }
    }

    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
}