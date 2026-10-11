package com.example.vuvur

import com.example.vuvur.data.SettingsRepository
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface VuvurApiService {
    @GET("/api/gallery")
    suspend fun getFiles(
        @Query("sort") sortBy: String,
        @Query("q") query: String,
        @Query("page") page: Int,
        @Query("group") group: String?,
        @Query("subgroup") subgroup: String?
    ): PaginatedFileResponse

    @GET("/api/gallery/groups")
    suspend fun getGroups(): List<GroupInfo>

    @GET("/api/gallery/subgroups")
    suspend fun getSubgroups(@Query("group") group: String): List<String>

    @GET("/api/scan/status")
    suspend fun getScanStatus(): ScanStatusResponse

    @GET("/api/files/random")
    suspend fun getRandomFiles(@Query("count") count: Int): List<MediaFile>

    @GET("/api/random-single")
    suspend fun getRandomSingle(@Query("q") query: String): MediaFile

    @POST("/api/cache/cleanup")
    suspend fun cleanCache(): CleanupResponse

    @POST("/api/delete/{id}")
    suspend fun deleteMediaItem(@Path("id") mediaId: Int): DeleteResponse
}

class ApiClient(private val repository: SettingsRepository) {

    companion object {
        private const val DUMMY_URL = "http://localhost/"
    }

    // ✅ Make sure this function signature accepts two arguments
    fun createService(baseUrl: String, apiKey: String?): VuvurApiService {
        val interceptor = Interceptor { chain ->
            val newUrl = baseUrl.toHttpUrl()

            val requestBuilder = chain.request().newBuilder()
                .url(
                    chain.request().url.newBuilder()
                        .scheme(newUrl.scheme)
                        .host(newUrl.host)
                        .port(newUrl.port)
                        .build()
                )

            // ✅ Conditionally add the header
            apiKey?.let {
                requestBuilder.header("X-Api-Key", it)
            }

            chain.proceed(requestBuilder.build())
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(interceptor)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(DUMMY_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        return retrofit.create(VuvurApiService::class.java)
    }
}