package com.example.vuvur.data

import android.content.Context
import coil.ImageLoader
import coil.decode.DataSource
import coil.fetch.FetchResult
import coil.fetch.Fetcher
import coil.fetch.SourceResult
import coil.request.Options
import com.example.vuvur.VuvurApplication
import okio.Buffer

class OfflineMediaFetcher(
    private val data: OfflineMediaItem,
    private val options: Options
) : Fetcher {

    override suspend fun fetch(): FetchResult? {
        val isImage = data.type.lowercase().let { it == "image" || it == "gif" }
        if (!isImage) return null // Currently, we only fetch images/thumbnails

        try {
            val app = options.context.applicationContext as VuvurApplication
            val plainBytes = app.offlineRepository.decryptToBytes(options.context, data)
            
            // Provide the decrypted bytes to Coil as a buffer
            val buffer = Buffer().apply { write(plainBytes) }
            return SourceResult(
                source = coil.decode.ImageSource(buffer, options.context),
                mimeType = null,
                dataSource = DataSource.DISK
            )
        } catch (e: Exception) {
            e.printStackTrace()
            return null
        }
    }

    class Factory : Fetcher.Factory<OfflineMediaItem> {
        override fun create(
            data: OfflineMediaItem,
            options: Options,
            imageLoader: ImageLoader
        ): Fetcher {
            return OfflineMediaFetcher(data, options)
        }
    }
}
