package com.example.vuvur.screens

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.vuvur.GalleryUiState
import com.example.vuvur.GroupInfo
import com.example.vuvur.VuvurApplication
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow // Use StateFlow for external exposure
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException

class MediaViewModel(application: Application) : AndroidViewModel(application) {

    private val app = application as VuvurApplication
    private val repository = app.settingsRepository
    private var apiService = app.vuvurApiService

    private val _uiState = MutableStateFlow<GalleryUiState>(GalleryUiState.Loading())
    val uiState: StateFlow<GalleryUiState> = _uiState.asStateFlow()

    private var pollingJob: Job? = null
    private var currentSort = "random"
    private var currentQuery = ""
    private var currentGroupTag: String? = null
    private var currentSubgroupTag: String? = null
    private var fetchSubgroupsJob: Job? = null

    // No temporary storage needed in this approach
    // private var lastFetchedSubgroups: Pair<String, List<String>>? = null

    init {
        // Observe repository changes (remains the same)
        viewModelScope.launch {
            repository.refreshTrigger.collectLatest {
                refresh()
            }
        }
        viewModelScope.launch {
            repository.apiChanged.collectLatest { newApiUrl ->
                // ✅ Get the key for the new URL
                val newApiKey = repository.getApiKeyForUrl(newApiUrl)
                // ✅ Pass both to createService
                apiService = app.apiClient.createService(newApiUrl, newApiKey)
                refresh()
            }
        }
        viewModelScope.launch {
            repository.zoomChanged.collect { newZoomLevel ->
                _uiState.update { currentState ->
                    if (currentState is GalleryUiState.Success) {
                        currentState.copy(zoomLevel = newZoomLevel)
                    } else {
                        currentState
                    }
                }
            }
        }
        loadPage(1, isNewSearch = true)
    }

    fun applySearch(query: String) {
        currentQuery = query
        currentGroupTag = null
        currentSubgroupTag = null
        fetchSubgroupsJob?.cancel()
        _uiState.update {
            if (it is GalleryUiState.Success) {
                it.copy(
                    selectedGroupTag = null,
                    selectedSubgroupTag = null,
                    subgroups = emptyList(),
                    isLoadingSubgroups = false
                )
            } else { it } // Or transition to Loading
        }
        loadPage(1, isNewSearch = true)
    }

    fun applySort(sortBy: String) {
        currentSort = sortBy
        loadPage(1, isNewSearch = true)
    }

    // ✅ Modified applyGroupFilter
    fun applyGroupFilter(groupTag: String?) {
        println("BBB applyGroupFilter called with groupTag: $groupTag (current: $currentGroupTag)")
        if (currentGroupTag != groupTag) {
            println("BBB Group tag changed.")
            currentGroupTag = groupTag
            currentSubgroupTag = null // Reset subgroup selection
            fetchSubgroupsJob?.cancel() // Cancel previous fetch

            // Update state FIRST to show loading/selection change immediately
            _uiState.update { currentState ->
                // Always try to update, even from Loading/Error state if possible
                val currentGroups = (currentState as? GalleryUiState.Success)?.groups ?: emptyList() // Preserve groups list
                val currentFiles = (currentState as? GalleryUiState.Success)?.files ?: emptyList() // Preserve files temporarily
                // Preserve other fields too if needed, or transition cleanly

                // If currently Success, update subgroup flags
                if (currentState is GalleryUiState.Success) {
                    println("BBB applyGroupFilter: Updating UI state (from Success) -> selectedGroupTag=$groupTag, isLoadingSubgroups=${groupTag != null}")
                    currentState.copy(
                        selectedGroupTag = groupTag,
                        selectedSubgroupTag = null,
                        subgroups = emptyList(), // Clear subgroups visually
                        isLoadingSubgroups = groupTag != null // Show loading only if fetching
                    )
                }
                // If not success, consider going to Loading state before fetch/loadPage,
                // or just update internal tags and let next loadPage handle UI state.
                // For simplicity, we'll let loadPage handle non-Success state transitions.
                // Just ensure internal tags are set correctly.
                else {
                    println("BBB applyGroupFilter: State is ${currentState::class.simpleName}, only updating internal tags.")
                    currentState // Keep current non-Success state for now
                }
            }

            // Fetch subgroups OR call loadPage directly
            if (groupTag != null) {
                println("BBB Calling fetchSubgroups for $groupTag (will trigger loadPage on completion)")
                fetchSubgroups(groupTag) // fetchSubgroups will now call loadPage
            } else {
                println("BBB Group tag is null (All selected). Calling loadPage directly.")
                loadPage(1, isNewSearch = true) // No subgroups to fetch, just load gallery items
            }
        } else {
            println("BBB Group tag ($groupTag) did not change. No action taken.")
        }
    }


    fun applySubgroupFilter(subgroupTag: String?) {
        println("BBB applySubgroupFilter called with subgroupTag: $subgroupTag (current: $currentSubgroupTag)")
        if (currentSubgroupTag != subgroupTag) {
            println("BBB Subgroup tag changed.")
            currentSubgroupTag = subgroupTag

            // Update UI state immediately
            _uiState.update { currentState ->
                if (currentState is GalleryUiState.Success) {
                    println("BBB Updating UI state: setting selectedSubgroupTag=$subgroupTag")
                    currentState.copy(selectedSubgroupTag = subgroupTag)
                } else {
                    println("BBB State is not Success during subgroup filter update.")
                    currentState
                }
            }

            // Call loadPage directly AFTER state update
            println("BBB Calling loadPage(1, true) after applying subgroup filter.")
            loadPage(1, isNewSearch = true) // Reload gallery for the new subgroup
        } else {
            println("BBB Subgroup tag ($subgroupTag) did not change. No action taken.")
        }
    }

    // ✅ Modified fetchSubgroups to call loadPage on completion/error
    private fun fetchSubgroups(groupTag: String) {
        fetchSubgroupsJob?.cancel()
        fetchSubgroupsJob = viewModelScope.launch(Dispatchers.IO) {
            println("BBB fetchSubgroups started for: $groupTag")
            var subgroupsResult: List<String> = emptyList() // Default to empty list
            var fetchSuccess = false
            try {
                println("BBB Calling apiService.getSubgroups...")
                subgroupsResult = apiService.getSubgroups(groupTag)
                fetchSuccess = true
                println("BBB Subgroups fetched successfully: $subgroupsResult")

            } catch (e: Exception) {
                if (e !is kotlinx.coroutines.CancellationException) {
                    println("BBB FAILED to fetch subgroups for $groupTag: ${e::class.simpleName} - ${e.message}")
                    // Keep subgroupsResult as emptyList
                } else {
                    println("BBB fetchSubgroups cancelled for $groupTag.")
                    return@launch // Don't proceed if cancelled
                }
            } finally {
                println("BBB fetchSubgroups finally block. Success=$fetchSuccess. Updating state and calling loadPage.")
                // Update state with result (or empty) and set loading false
                _uiState.update { currentState ->
                    if (currentState is GalleryUiState.Success && currentState.selectedGroupTag == groupTag) {
                        currentState.copy(
                            subgroups = subgroupsResult, // Use fetched result (or empty on error)
                            isLoadingSubgroups = false // Finish loading
                        ).also { println("BBB Updated subgroup state: isLoading=${it.isLoadingSubgroups}, list=${it.subgroups}") }
                    } else {
                        println("BBB State condition not met in fetchSubgroups finally. State: ${currentState::class.simpleName}, SelectedGroup: ${(currentState as? GalleryUiState.Success)?.selectedGroupTag}, FetchedFor: $groupTag. Skipping state update.")
                        currentState // Don't update if group changed or state isn't Success
                    }
                }
                // ✅ Trigger gallery load AFTER updating subgroup state
                println("BBB fetchSubgroups triggering loadPage(1, true) after completion/error.")
                loadPage(1, isNewSearch = true)
            }
        }
    }


    // deleteMediaItem remains the same
    fun deleteMediaItem(mediaId: Int) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                apiService.deleteMediaItem(mediaId)
                _uiState.update { currentState ->
                    if (currentState is GalleryUiState.Success) {
                        currentState.copy(files = currentState.files.filterNot { file -> file.id == mediaId })
                    } else {
                        currentState
                    }
                }
            } catch (e: Exception) {
                println("Failed to delete item $mediaId: ${e.message}")
            }
        }
    }


    // loadPage remains mostly the same, simplified state preservation
    fun loadPage(page: Int, isNewSearch: Boolean = false) {
        viewModelScope.launch(Dispatchers.IO) {
            val currentStateValue = _uiState.value
            println("BBB loadPage($page, isNewSearch=$isNewSearch) called. Current state: ${currentStateValue::class.simpleName}")

            if (currentStateValue is GalleryUiState.Success && currentStateValue.isLoadingNextPage) {
                println("BBB loadPage cancelled: Already loading next page.")
                return@launch
            }
            if (currentStateValue is GalleryUiState.Success && !isNewSearch && page > currentStateValue.totalPages) {
                println("BBB loadPage cancelled: Reached last page.")
                return@launch
            }

            val activeApiUrl = repository.activeApiUrlFlow.first()
            val activeApiKey = repository.getApiKeyForUrl(activeApiUrl)
            val activeApiAlias = repository.getAliasForUrl(activeApiUrl)
            val zoomLevel = repository.zoomLevelFlow.first()
            val previousSuccessState = currentStateValue as? GalleryUiState.Success
            var groups: List<GroupInfo> = previousSuccessState?.groups ?: emptyList()
            // Preserve necessary flags from previous state
            var isLoadingSubgroups = previousSuccessState?.isLoadingSubgroups ?: false
            var currentSubgroupsList = previousSuccessState?.subgroups ?: emptyList()


            if (isNewSearch) {
                println("BBB loadPage: isNewSearch = true. Setting state to Loading.")
                // Set Loading state, try to preserve essential info across the transition
                _uiState.value = GalleryUiState.Loading(activeApiUrl, activeApiAlias)
                try {
                    println("BBB loadPage: Fetching groups...")
                    groups = apiService.getGroups()
                    println("BBB loadPage: Groups fetched: ${groups.size} items.")
                } catch (e: Exception) {
                    println("BBB loadPage: Failed to fetch groups: ${e.message}")
                    groups = emptyList()
                }
                // Determine isLoadingSubgroups based on current selection (it might have been set true by applyGroupFilter)
                isLoadingSubgroups = currentGroupTag != null && previousSuccessState?.isLoadingSubgroups == true
                currentSubgroupsList = if(currentGroupTag != null) previousSuccessState?.subgroups ?: emptyList() else emptyList()
                println("BBB loadPage: isNewSearch=true. Preserving isLoadingSubgroups = $isLoadingSubgroups, subgroupsSize = ${currentSubgroupsList.size}")

            } else if (currentStateValue is GalleryUiState.Success) {
                println("BBB loadPage: Loading next page ($page). Setting isLoadingNextPage = true.")
                _uiState.value = currentStateValue.copy(isLoadingNextPage = true)
                // Preserve subgroup state
                isLoadingSubgroups = currentStateValue.isLoadingSubgroups
                currentSubgroupsList = currentStateValue.subgroups
            } else {
                println("BBB loadPage: Current state is ${currentStateValue::class.simpleName}. Setting Loading state.")
                _uiState.value = GalleryUiState.Loading(activeApiUrl, activeApiAlias)
                // Determine subgroup state based on current filter tags
                isLoadingSubgroups = currentGroupTag != null // If a group is selected, assume loading might be needed
                currentSubgroupsList = emptyList() // No previous state to preserve list from
            }

            try {
                println("BBB loadPage: Calling apiService.getFiles (page=$page, group=$currentGroupTag, subgroup=$currentSubgroupTag)...")
                val response = apiService.getFiles(
                    sortBy = currentSort,
                    query = currentQuery,
                    page = page,
                    group = currentGroupTag,
                    subgroup = currentSubgroupTag
                )
                println("BBB loadPage: getFiles response received (items=${response.items.size}, totalPages=${response.total_pages})")

                // Update state based on the LATEST state ('it'), merging results
                _uiState.update { latestState ->
                    println("BBB loadPage: Updating final state (latestState is ${latestState::class.simpleName})")
                    val previousFiles = if (isNewSearch || latestState !is GalleryUiState.Success) {
                        emptyList()
                    } else {
                        latestState.files
                    }
                    val newItems = if (isNewSearch) response.items else response.items.filter { newItem -> previousFiles.none { it.id == newItem.id } }

                    // Inherit subgroup state from latestState if it's Success, otherwise use values preserved above
                    val finalSubgroups = (latestState as? GalleryUiState.Success)?.subgroups ?: currentSubgroupsList
                    val finalIsLoadingSubgroups = (latestState as? GalleryUiState.Success)?.isLoadingSubgroups ?: isLoadingSubgroups

                    println("BBB loadPage: Final state update - isLoadingSubgroups=$finalIsLoadingSubgroups, subgroupsSize=${finalSubgroups.size}")

                    GalleryUiState.Success(
                        files = previousFiles + newItems,
                        totalPages = response.total_pages,
                        currentPage = response.page,
                        isLoadingNextPage = false,
                        activeApiUrl = activeApiUrl,
                        activeApiAlias = activeApiAlias,
                        activeApiKey = activeApiKey,
                        zoomLevel = zoomLevel,
                        groups = groups,
                        selectedGroupTag = currentGroupTag,
                        subgroups = finalSubgroups,
                        selectedSubgroupTag = currentSubgroupTag,
                        isLoadingSubgroups = finalIsLoadingSubgroups
                    ).also { println("BBB loadPage: Final Success state constructed.") }
                }
            } catch (e: HttpException) {
                println("BBB loadPage: HttpException occurred: ${e.code()} ${e.message()}")
                handleApiError(e)
            } catch (e: Exception) {
                if (e is kotlinx.coroutines.CancellationException) {
                    println("BBB loadPage: Job cancelled.")
                    // Ensure loading flags are reset if cancelled
                    _uiState.update {
                        when(it) {
                            is GalleryUiState.Success -> it.copy(isLoadingNextPage = false, isLoadingSubgroups = false) // Also reset subgroup loading on cancel?
                            is GalleryUiState.Loading -> GalleryUiState.Error("Load cancelled") // Or go to error?
                            else -> it
                        }
                    }
                } else {
                    println("BBB loadPage: Exception occurred: ${e.message}")
                    // Set error state, especially if it was an initial load
                    if (isNewSearch || currentStateValue !is GalleryUiState.Success) {
                        _uiState.value = GalleryUiState.Error(
                            message = e.message ?: "Unknown error loading gallery",
                            activeApiAlias = activeApiAlias
                        )
                    } else {
                        // If loading next page failed, just reset the flag, keep existing data
                        _uiState.update { if (it is GalleryUiState.Success) it.copy(isLoadingNextPage = false) else it}
                        println("BBB loadPage: Failed to load next page, showing previous data.")
                        // Maybe show a snackbar here?
                    }
                }
            }
        }
    }


    // handleApiError remains the same
    private fun handleApiError(e: HttpException) {
        viewModelScope.launch(Dispatchers.IO) {
            val activeApiUrl = repository.activeApiUrlFlow.first()
            val activeApiAlias = repository.getAliasForUrl(activeApiUrl)
            try {
                val scanStatus = apiService.getScanStatus()
                if (!scanStatus.scan_complete) {
                    _uiState.value = GalleryUiState.Scanning(
                        progress = scanStatus.progress,
                        total = scanStatus.total,
                        activeApiAlias = activeApiAlias
                    )
                    startPollingForScanStatus()
                } else {
                    _uiState.value = GalleryUiState.Error(
                        message = "Error: ${e.code()} ${e.message()}",
                        activeApiAlias = activeApiAlias
                    )
                }
            } catch (innerE: Exception) {
                println("Error handling API error: ${innerE.message}")
                _uiState.value = GalleryUiState.Error(
                    message = e.message ?: "Failed to connect or get scan status",
                    activeApiAlias = activeApiAlias
                )
            }
        }
    }


    // startPollingForScanStatus remains the same
    private fun startPollingForScanStatus() {
        if (pollingJob?.isActive == true) return
        pollingJob = viewModelScope.launch(Dispatchers.IO) {
            val activeApiUrl = repository.activeApiUrlFlow.first()
            val activeApiAlias = repository.getAliasForUrl(activeApiUrl)
            while (true) {
                delay(2000)
                try {
                    val status = apiService.getScanStatus()
                    if (status.scan_complete) {
                        refresh() // Call the main refresh method now
                        break
                    } else {
                        _uiState.update { currentState ->
                            if (currentState is GalleryUiState.Scanning) {
                                currentState.copy(
                                    progress = status.progress,
                                    total = status.total,
                                    activeApiAlias = activeApiAlias
                                )
                            } else {
                                currentState // Stop updating if state changed
                            }
                        }
                    }
                } catch (e: Exception) {
                    println("Error during scan status polling: ${e.message}")
                    delay(5000)
                }
            }
        }
    }

    // refresh remains the same (calls loadPage)
    fun refresh(resetSubgroups: Boolean = true) {
        println("BBB refresh called (resetSubgroups=$resetSubgroups)")
        pollingJob?.cancel()
        fetchSubgroupsJob?.cancel()

        if (resetSubgroups) {
            println("BBB refresh: Resetting group and subgroup selection.")
            currentGroupTag = null // Reset group too on full refresh
            currentSubgroupTag = null
            // lastFetchedSubgroups = null // No longer used
        }
        loadPage(1, isNewSearch = true)
    }
}
