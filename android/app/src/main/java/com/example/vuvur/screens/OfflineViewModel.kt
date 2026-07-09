package com.example.vuvur.screens

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.vuvur.MediaFile
import com.example.vuvur.VuvurApplication
import com.example.vuvur.data.OfflineMediaItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.io.File

class OfflineViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as VuvurApplication
    private val offlineRepo = app.offlineRepository

    val offlineItems: StateFlow<List<OfflineMediaItem>> = offlineRepo.offlineItemsFlow
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    val usedStorageBytes: StateFlow<Long> = offlineRepo.offlineItemsFlow
        .map { items -> items.sumOf { it.sizeBytes } }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = 0L
        )

    // Expose cache mode so screens can decide whether to trigger caching
    val cacheModeFlow: StateFlow<String> = app.settingsRepository.offlineCacheModeFlow
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = "ON_TAP"
        )

    /**
     * Saves a media item offline. Call this from:
     * - GalleryScreen grid items (when mode == "ALL")
     * - ViewerScreen page change (when mode == "ON_TAP" or always)
     */
    fun saveItem(mediaFile: MediaFile, apiUrl: String, apiKey: String?) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                offlineRepo.saveMediaOffline(app, mediaFile, apiUrl, apiKey)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    fun deleteItem(item: OfflineMediaItem) {
        viewModelScope.launch(Dispatchers.IO) {
            offlineRepo.deleteOfflineItem(app, item)
        }
    }

    suspend fun decryptToTempFile(item: OfflineMediaItem): File {
        return offlineRepo.decryptToTempFile(app, item)
    }
}
