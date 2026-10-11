package com.example.vuvur

import com.google.gson.annotations.SerializedName

data class MediaFile(
    val id: Int,
    val path: String,
    val type: String,
    val width: Int,
    val height: Int,
    val mod_time: Double,
    val exif: Map<String, Any> = emptyMap()
)

data class PaginatedFileResponse(
    val total_items: Int,
    val page: Int,
    val total_pages: Int,
    val items: List<MediaFile>
)

data class GroupInfo(
    @SerializedName("group_tag")
    val groupTag: String,
    val count: Int
)

data class ScanStatusResponse(
    val scan_complete: Boolean,
    val progress: Int,
    val total: Int
)

data class CleanupResponse(
    val message: String,
    val deleted_files: Int // Assuming API might provide this, adjust if not
)

data class DeleteResponse(
    val status: String,
    val message: String
)

sealed interface GalleryUiState {
    data class Loading(
        val apiUrl: String? = null,
        val apiAlias: String? = null
    ) : GalleryUiState

    data class Scanning(
        val progress: Int,
        val total: Int,
        val activeApiAlias: String = ""
    ) : GalleryUiState

    data class Error(
        val message: String,
        val activeApiAlias: String = ""
    ) : GalleryUiState
    data class Success(
        val files: List<MediaFile> = emptyList(),
        val totalPages: Int = 1,
        val currentPage: Int = 1,
        val isLoadingNextPage: Boolean = false,
        val activeApiUrl: String,
        val activeApiAlias: String = "",
        // ✅ Add the API key to the success state
        val activeApiKey: String?,
        val zoomLevel: Float = 2.5f,
        val groups: List<GroupInfo> = emptyList(),
        val selectedGroupTag: String? = null,
        // ✅ Add subgroups state
        val subgroups: List<String> = emptyList(),
        val selectedSubgroupTag: String? = null,
        val isLoadingSubgroups: Boolean = false // Track subgroup loading
    ) : GalleryUiState
}