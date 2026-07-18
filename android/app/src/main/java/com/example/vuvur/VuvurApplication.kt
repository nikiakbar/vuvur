package com.example.vuvur

import android.app.Application
import coil.ImageLoader
import coil.ImageLoaderFactory
import coil.decode.ImageDecoderDecoder
import com.example.vuvur.data.OfflineRepository
import com.example.vuvur.data.SettingsRepository
import com.example.vuvur.data.dataStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.ResponseBody.Companion.toResponseBody

// Define the CoroutineScope at the application level
private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

// Implement ImageLoaderFactory
class VuvurApplication : Application(), ImageLoaderFactory {
    // Initialize repository using the imported dataStore and applicationScope
    val settingsRepository by lazy {
        SettingsRepository(dataStore, applicationScope)
    }
    val offlineRepository by lazy {
        OfflineRepository(settingsRepository)
    }
    val apiClient by lazy {
        ApiClient(settingsRepository)
    }
    lateinit var vuvurApiService: VuvurApiService

    override fun onCreate() {
        super.onCreate()
        // Initialize ApiService asynchronously
        applicationScope.launch {
            // Fetch initial URL using the suspend function from the initialized repository
            val activeUrl = settingsRepository.getActiveApiUrl()
            // Get the corresponding API key
            val activeApiKey = settingsRepository.getApiKeyForUrl(activeUrl)
            // Pass both to the createService method
            vuvurApiService = apiClient.createService(activeUrl, activeApiKey)
        }
    }

    // Override newImageLoader to provide a custom instance
    override fun newImageLoader(): ImageLoader {
        // ✅ Create a custom OkHttpClient for Coil
        val coilOkHttpClient = OkHttpClient.Builder()
            .addInterceptor { chain ->
                // Block ALL network requests when duress mode is active.
                // Return a fake empty 200 so Coil fails gracefully without making any call.
                if (DuressState.isActive) {
                    return@addInterceptor Response.Builder()
                        .request(chain.request())
                        .protocol(Protocol.HTTP_1_1)
                        .code(200)
                        .message("OK")
                        .body(ByteArray(0).toResponseBody())
                        .build()
                }

                // This interceptor will run for every image request
                // ✅ Use runBlocking to synchronously get the current URL and Key
                // This is safe because Coil runs this on a background thread.
                val (activeUrl, apiKey) = runBlocking(Dispatchers.IO) {
                    val url = settingsRepository.activeApiUrlFlow.first()
                    val key = settingsRepository.getApiKeyForUrl(url)
                    url to key
                }

                // ✅ Build the new request, adding the API key if it exists
                val newRequest = chain.request().newBuilder().apply {
                    apiKey?.let {
                        header("X-Api-Key", it)
                    }
                }.build()

                chain.proceed(newRequest)
            }
            .build()

        return ImageLoader.Builder(this)
            // ✅ Tell Coil to use our custom OkHttpClient
            .okHttpClient(coilOkHttpClient)
            .components {
                add(ImageDecoderDecoder.Factory())
                add(com.example.vuvur.data.OfflineMediaFetcher.Factory())
            }
            .crossfade(true) // Optional: for smooth image loading
            .build()
    }
}