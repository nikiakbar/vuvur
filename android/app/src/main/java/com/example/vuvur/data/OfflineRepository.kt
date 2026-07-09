package com.example.vuvur.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import com.example.vuvur.MediaFile
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.UUID

class StorageQuotaExceededException(limitGb: Float) :
    Exception("Offline storage quota of ${limitGb}GB exceeded")

class OfflineRepository(
    private val settingsRepository: SettingsRepository
) {

    companion object {
        private const val OFFLINE_DIR = "offline"
        private val IMAGE_TYPES = setOf("image", "gif")
        private const val JPEG_QUALITY = 85
    }

    // Shared OkHttp client for downloading media bytes
    private val httpClient = OkHttpClient.Builder().build()

    // Expose the index as a Flow
    val offlineItemsFlow = settingsRepository.offlineIndexFlow

    /**
     * Downloads, compresses (images only), encrypts, and stores a media item locally.
     * Skips silently if the item is already cached.
     * Enforces the user-configured storage quota.
     */
    suspend fun saveMediaOffline(
        context: Context,
        mediaFile: MediaFile,
        apiUrl: String,
        apiKey: String?
    ): Result<Unit> = runCatching {
        val existingIndex = settingsRepository.getOfflineIndex()

        // Skip if already cached by server ID
        if (existingIndex.any { it.id == mediaFile.id }) return@runCatching

        // Determine URL: use stream endpoint for video, thumbnail for image
        val isImage = mediaFile.type.lowercase().let { it == "image" || it == "gif" }
        val mediaUrl = if (isImage) {
            "$apiUrl/api/thumbnails/${mediaFile.id}?original=true"
        } else {
            "$apiUrl/api/stream/${mediaFile.id}"
        }

        // Download raw bytes
        val rawBytes = downloadBytes(mediaUrl, apiKey)

        // Compress images; leave videos as-is (already compressed)
        val processedBytes = if (isImage) {
            compressImage(rawBytes)
        } else {
            rawBytes
        }

        // Check quota before encrypting/writing
        val limitGb = settingsRepository.offlineStorageLimitGbFlow.first()
        val limitBytes = (limitGb * 1024 * 1024 * 1024).toLong()
        val currentUsed = existingIndex.sumOf { it.sizeBytes }
        val estimatedNewSize = processedBytes.size.toLong() + 28L // +28 for IV + GCM tag overhead
        if (currentUsed + estimatedNewSize > limitBytes) {
            throw StorageQuotaExceededException(limitGb)
        }

        // Encrypt
        val encryptedBytes = CryptoManager.encrypt(processedBytes)

        // Write to filesDir/offline/<uuid>
        val offlineDir = File(context.filesDir, OFFLINE_DIR).apply { mkdirs() }
        val fileName = UUID.randomUUID().toString()
        val outFile = File(offlineDir, fileName)
        outFile.writeBytes(encryptedBytes)

        // Update index
        val newItem = OfflineMediaItem(
            id = mediaFile.id,
            fileName = fileName,
            type = mediaFile.type,
            width = mediaFile.width,
            height = mediaFile.height,
            savedAt = System.currentTimeMillis(),
            sizeBytes = outFile.length()
        )
        settingsRepository.saveOfflineIndex(existingIndex + newItem)
    }

    /**
     * Decrypts a cached item to a temporary file for playback.
     * Returns the temp [File]; caller is responsible for deleting it after use.
     */
    suspend fun decryptToTempFile(context: Context, item: OfflineMediaItem): File {
        val offlineDir = File(context.filesDir, OFFLINE_DIR)
        val encryptedFile = File(offlineDir, item.fileName)
        val encryptedBytes = encryptedFile.readBytes()
        val plainBytes = CryptoManager.decrypt(encryptedBytes)

        val ext = if (item.type.lowercase() == "image" || item.type.lowercase() == "gif") "jpg" else "mp4"
        val tempFile = File(context.cacheDir, "offline_temp_${item.id}.$ext")
        tempFile.writeBytes(plainBytes)
        return tempFile
    }

    /**
     * Deletes a cached item from disk and removes it from the index.
     */
    suspend fun deleteOfflineItem(context: Context, item: OfflineMediaItem) {
        val offlineDir = File(context.filesDir, OFFLINE_DIR)
        File(offlineDir, item.fileName).delete()
        val updatedIndex = settingsRepository.getOfflineIndex().filterNot { it.id == item.id }
        settingsRepository.saveOfflineIndex(updatedIndex)
    }

    /**
     * Deletes all cached items and clears the index.
     */
    suspend fun clearAllOfflineMedia(context: Context) {
        val offlineDir = File(context.filesDir, OFFLINE_DIR)
        offlineDir.listFiles()?.forEach { it.delete() }
        settingsRepository.saveOfflineIndex(emptyList())
    }

    /**
     * Returns the total bytes consumed by all offline files on disk.
     */
    fun getTotalUsedBytes(context: Context): Long {
        val offlineDir = File(context.filesDir, OFFLINE_DIR)
        return offlineDir.listFiles()?.sumOf { it.length() } ?: 0L
    }

    // ---- private helpers ----

    private fun downloadBytes(url: String, apiKey: String?): ByteArray {
        val requestBuilder = Request.Builder().url(url)
        apiKey?.let { requestBuilder.header("X-Api-Key", it) }
        val response = httpClient.newCall(requestBuilder.build()).execute()
        if (!response.isSuccessful) {
            throw Exception("Failed to download media: HTTP ${response.code}")
        }
        return response.body?.bytes() ?: throw Exception("Empty response body")
    }

    private fun compressImage(rawBytes: ByteArray): ByteArray {
        val bitmap = BitmapFactory.decodeByteArray(rawBytes, 0, rawBytes.size)
            ?: return rawBytes // fallback: store as-is if decode fails
        val out = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, out)
        bitmap.recycle()
        return out.toByteArray()
    }
}
