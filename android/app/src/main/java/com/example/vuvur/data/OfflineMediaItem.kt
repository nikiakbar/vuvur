package com.example.vuvur.data

/**
 * Represents a single media item that has been saved to the local encrypted offline store.
 */
data class OfflineMediaItem(
    val id: Int,           // original server media ID
    val fileName: String,  // encrypted file name on disk (UUID-based, no extension)
    val type: String,      // "image" or "video"
    val width: Int,
    val height: Int,
    val savedAt: Long,     // epoch milliseconds
    val sizeBytes: Long    // size of the encrypted file on disk
)
