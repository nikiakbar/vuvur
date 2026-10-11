package com.example.vuvur.components

import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.datasource.DefaultHttpDataSource // ✅ Import
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory // ✅ Import
import androidx.media3.ui.PlayerView
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.example.vuvur.MediaFile

@Composable
fun MediaSlide(
    file: MediaFile,
    activeApiUrl: String,
    // ✅ Accept the API key
    activeApiKey: String?,
    onNextImage: () -> Unit,
    onPreviousImage: () -> Unit,
    allowSwipeNavigation: Boolean = true,
    // ✅ Add zoom level as a parameter
    doubleTapZoomLevel: Float = 2.5f
) {
    val context = LocalContext.current

    var scale by remember { mutableStateOf(1f) }
    var offsetX by remember { mutableStateOf(0f) }
    var offsetY by remember { mutableStateOf(0f) }

    // Reset zoom/pan when file changes
    LaunchedEffect(file) {
        scale = 1f
        offsetX = 0f
        offsetY = 0f
    }

    BoxWithConstraints(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        val containerWidth = constraints.maxWidth.toFloat()
        val containerHeight = constraints.maxHeight.toFloat()

        fun maxOffsets(currentScale: Float): Pair<Float, Float> {
            val maxX = (containerWidth * (currentScale - 1f)) / 2f
            val maxY = (containerHeight * (currentScale - 1f)) / 2f
            return Pair(maxX.coerceAtLeast(0f), maxY.coerceAtLeast(0f))
        }

        LaunchedEffect(scale) {
            if (scale > 1f) {
                val (mx, my) = maxOffsets(scale)
                offsetX = offsetX.coerceIn(-mx, mx)
                offsetY = offsetY.coerceIn(-my, my)
            } else {
                offsetX = 0f
                offsetY = 0f
            }
        }

        val dragModifier = if (scale > 1f) {
            Modifier.pointerInput(scale) {
                detectDragGestures { change, dragAmount ->
                    val (dx, dy) = dragAmount
                    val (mx, my) = maxOffsets(scale)
                    offsetX = (offsetX + dx).coerceIn(-mx, mx)
                    offsetY = (offsetY + dy).coerceIn(-my, my)
                    change.consume()
                }
            }
        } else Modifier

        Box(
            modifier = Modifier
                .fillMaxSize()
                .pointerInput(scale) {
                    detectTapGestures(
                        onDoubleTap = { tapOffset ->
                            if (file.type == "image") {
                                if (scale <= 1f) {
                                    // ✅ Use the passed-in zoom level
                                    val targetScale = doubleTapZoomLevel
                                    val tx = (containerWidth / 2f - tapOffset.x) * (targetScale - 1f)
                                    val ty = (containerHeight / 2f - tapOffset.y) * (targetScale - 1f)
                                    scale = targetScale
                                    val (mx, my) = maxOffsets(scale)
                                    offsetX = tx.coerceIn(-mx, mx)
                                    offsetY = ty.coerceIn(-my, my)
                                } else {
                                    scale = 1f
                                    offsetX = 0f
                                    offsetY = 0f
                                }
                            }
                        }
                    )
                }
                .then(dragModifier)
        ) {
            if (file.type == "image") {
                AsyncImage(
                    model = ImageRequest.Builder(context)
                        .data("$activeApiUrl/api/stream/${file.id}")
                        .crossfade(true)
                        .build(),
                    contentDescription = file.path,
                    modifier = Modifier
                        .graphicsLayer(
                            scaleX = scale,
                            scaleY = scale,
                            translationX = offsetX,
                            translationY = offsetY
                        )
                        .fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
            } else {
                // ✅ This is the new, more robust ExoPlayer block
                val exoPlayer = remember(file, activeApiKey) {

                    // 1. Create an HTTP data source factory
                    val httpDataSourceFactory = DefaultHttpDataSource.Factory()

                    // 2. Conditionally set the API key in the default headers
                    if (activeApiKey != null) {
                        httpDataSourceFactory.setDefaultRequestProperties(
                            mapOf("X-Api-Key" to activeApiKey)
                        )
                    }

                    // 3. Create a MediaSourceFactory from the HTTP factory
                    val mediaSourceFactory = DefaultMediaSourceFactory(httpDataSourceFactory)

                    // 4. Build ExoPlayer, setting the MediaSourceFactory
                    ExoPlayer.Builder(context)
                        .setMediaSourceFactory(mediaSourceFactory) // <-- This is the key change
                        .build()
                        .apply {
                            // 5. The MediaItem is now just a simple URI
                            val mediaItem = MediaItem.fromUri("$activeApiUrl/api/stream/${file.id}")

                            // Configure and prepare the player
                            setMediaItem(mediaItem)
                            repeatMode = Player.REPEAT_MODE_ONE
                            prepare()
                            playWhenReady = true
                        }
                }

                DisposableEffect(Unit) {
                    onDispose { exoPlayer.release() }
                }

                AndroidView(
                    factory = {
                        PlayerView(it).apply {
                            player = exoPlayer
                            useController = true
                        }
                    },
                    modifier = Modifier.fillMaxSize()
                )
            }
        }
    }
}