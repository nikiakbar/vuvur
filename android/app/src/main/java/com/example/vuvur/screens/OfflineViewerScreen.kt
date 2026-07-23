package com.example.vuvur.screens

import android.net.Uri
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.VerticalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import coil.compose.AsyncImage
import com.example.vuvur.data.OfflineMediaItem
import java.io.File

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun OfflineViewerScreen(
    viewModel: OfflineViewModel,
    startIndex: Int,
    navController: NavController
) {
    val offlineItems by viewModel.offlineItems.collectAsState()
    var zoomedPageIndex by remember { mutableStateOf(-1) }
    val isPagerScrollEnabled = zoomedPageIndex == -1

    var showDeleteDialog by remember { mutableStateOf<OfflineMediaItem?>(null) }

    Box(modifier = Modifier.fillMaxSize()) {
        if (offlineItems.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No offline media found.")
            }
            return@Box
        }

        // Ensure startIndex is within bounds
        val validStartIndex = if (startIndex in offlineItems.indices) startIndex else 0

        val pagerState = rememberPagerState(
            initialPage = validStartIndex,
            pageCount = { offlineItems.size }
        )

        LaunchedEffect(pagerState.isScrollInProgress) {
            if (pagerState.isScrollInProgress) {
                zoomedPageIndex = -1
            }
        }

        VerticalPager(
            state = pagerState,
            userScrollEnabled = isPagerScrollEnabled,
            modifier = Modifier.fillMaxSize()
        ) { pageIndex ->
            val item = offlineItems.getOrNull(pageIndex)
            if (item != null) {
                OfflineMediaViewer(
                    item = item,
                    viewModel = viewModel,
                    isCurrentlyVisible = pageIndex == pagerState.currentPage
                )
            }
        }

        if (showDeleteDialog != null) {
            AlertDialog(
                onDismissRequest = { showDeleteDialog = null },
                title = { Text("Delete Offline File") },
                text = { Text("Are you sure you want to remove this file from offline storage?") },
                confirmButton = {
                    TextButton(
                        onClick = {
                            showDeleteDialog?.let { viewModel.deleteItem(it) }
                            showDeleteDialog = null
                            if (offlineItems.size <= 1) {
                                navController.popBackStack()
                            }
                        }
                    ) {
                        Text("Confirm")
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showDeleteDialog = null }) {
                        Text("Cancel")
                    }
                }
            )
        }

        // Close Button
        IconButton(
            onClick = { navController.popBackStack() },
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(16.dp),
            colors = IconButtonDefaults.iconButtonColors(
                containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f),
                contentColor = MaterialTheme.colorScheme.onSurface
            )
        ) {
            Icon(Icons.Default.Close, contentDescription = "Close Viewer")
        }

        // Delete Button
        IconButton(
            onClick = {
                val currentItem = offlineItems.getOrNull(pagerState.currentPage)
                if (currentItem != null) {
                    showDeleteDialog = currentItem
                }
            },
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(16.dp),
            colors = IconButtonDefaults.iconButtonColors(
                containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f),
                contentColor = MaterialTheme.colorScheme.onSurface
            )
        ) {
            Icon(Icons.Default.Delete, contentDescription = "Delete File")
        }
    }
}

@Composable
fun OfflineMediaViewer(
    item: OfflineMediaItem,
    viewModel: OfflineViewModel,
    isCurrentlyVisible: Boolean
) {
    var decryptedFile by remember { mutableStateOf<File?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var hasError by remember { mutableStateOf(false) }

    LaunchedEffect(item) {
        isLoading = true
        hasError = false
        try {
            decryptedFile = viewModel.decryptToTempFile(item)
        } catch (e: Exception) {
            hasError = true
            e.printStackTrace()
        } finally {
            isLoading = false
        }
    }

    DisposableEffect(item) {
        onDispose {
            // Clean up decrypted temp file
            decryptedFile?.delete()
            decryptedFile = null
        }
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        if (isLoading) {
            CircularProgressIndicator()
        } else if (hasError || decryptedFile == null) {
            Text("Error decrypting file.")
        } else {
            val isImage = item.type.lowercase().let { it == "image" || it == "gif" }
            if (isImage) {
                val containerWidth = constraints.maxWidth.toFloat()
                val containerHeight = constraints.maxHeight.toFloat()
                
                var scale by remember { mutableStateOf(1f) }
                var offsetX by remember { mutableStateOf(0f) }
                var offsetY by remember { mutableStateOf(0f) }

                LaunchedEffect(item) {
                    scale = 1f
                    offsetX = 0f
                    offsetY = 0f
                }
                
                LaunchedEffect(isCurrentlyVisible) {
                    if (!isCurrentlyVisible) {
                        scale = 1f
                        offsetX = 0f
                        offsetY = 0f
                    }
                }

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
                                    if (scale <= 1f) {
                                        val targetScale = 2.5f
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
                            )
                        }
                        .then(dragModifier)
                ) {
                    AsyncImage(
                        model = Uri.fromFile(decryptedFile),
                        contentDescription = "Offline Image",
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
                }
            } else {
                // Video playback logic. Since ExoPlayer setup is complex and MediaSlide 
                // is tightly coupled with network logic, we'd need a simpler video player here
                // or refactor MediaSlide. For this MVP, we'll just show a placeholder for video.
                // In a complete implementation, we would instantiate an ExoPlayer with a local File URI.
                Text("Offline video playback not fully implemented yet.")
            }
        }
    }
}
