package com.example.vuvur

import android.app.Application
import coil.ImageLoader
import coil.ImageLoaderFactory
import coil.decode.ImageDecoderDecoder
import com.example.vuvur.data.SettingsRepository
import com.example.vuvur.data.dataStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first // ✅ Import 'first'
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking // ✅ Import 'runBlocking'
import okhttp3.Interceptor // ✅ Import 'Interceptor'
import okhttp3.OkHttpClient // ✅ Import 'OkHttpClient'

// Define the CoroutineScope at the application level
private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

// Implement ImageLoaderFactory
class VuvurApplication : Application(), ImageLoaderFactory {
    // Initialize repository using the imported dataStore and applicationScope
    val settingsRepository by lazy {
        SettingsRepository(dataStore, applicationScope)
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
            }
            .crossfade(true) // Optional: for smooth image loading
            .build()
    }
}