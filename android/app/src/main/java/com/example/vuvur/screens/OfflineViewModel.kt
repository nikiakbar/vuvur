package com.example.vuvur.screens

import android.app.Application
import android.net.Uri
import androidx.core.content.FileProvider
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
import kotlinx.coroutines.isActive
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

    fun saveCurrentItem(mediaFile: MediaFile, apiUrl: String, apiKey: String?) {
        viewModelScope.launch(Dispatchers.IO) {
            offlineRepo.saveMediaOffline(app, mediaFile, apiUrl, apiKey)
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

    private var cacheAllJob: kotlinx.coroutines.Job? = null

    init {
        viewModelScope.launch {
            app.settingsRepository.offlineCacheModeFlow.collect { mode ->
                if (mode == "ALL") {
                    startCacheAllJob()
                } else {
                    cacheAllJob?.cancel()
                }
            }
        }
    }

    private fun startCacheAllJob() {
        if (cacheAllJob?.isActive == true) return
        
        cacheAllJob = viewModelScope.launch(Dispatchers.IO) {
            try {
                val apiUrl = app.settingsRepository.getActiveApiUrl()
                val apiKey = app.settingsRepository.getApiKeyForUrl(apiUrl)
                val apiService = app.apiClient.createService(apiUrl, apiKey)

                var currentPage = 1
                var hasMore = true

                while (hasMore && isActive) {
                    val response = apiService.getFiles(sortBy = "date_desc", query = "", page = currentPage, group = null, subgroup = null)
                    if (response.files.isEmpty()) {
                        hasMore = false
                    } else {
                        for (file in response.files) {
                            if (!isActive) break
                            try {
                                offlineRepo.saveMediaOffline(app, file, apiUrl, apiKey)
                            } catch (e: com.example.vuvur.data.StorageQuotaExceededException) {
                                // Reached limit and couldn't make space, stop caching
                                hasMore = false
                                break
                            } catch (e: Exception) {
                                e.printStackTrace() // Ignore network errors and continue
                            }
                        }
                        currentPage++
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
