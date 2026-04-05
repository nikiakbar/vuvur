package com.example.vuvur.screens

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.VerticalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
// ✅ Import Delete icon
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.example.vuvur.GalleryUiState
import com.example.vuvur.components.MediaSlide

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun ViewerScreen(
    viewModel: MediaViewModel,
    startIndex: Int,
    navController: NavController
) {
    val state by viewModel.uiState.collectAsState()
    var zoomedPageIndex by remember { mutableStateOf(-1) }
    val isPagerScrollEnabled = zoomedPageIndex == -1

    // ✅ State for delete confirmation
    var showDeleteDialog by remember { mutableStateOf<Int?>(null) }
    var currentFileId by remember { mutableStateOf<Int?>(null) }

    Box(modifier = Modifier.fillMaxSize()) {
        when (val currentState = state) {
            is GalleryUiState.Success -> {
                if (currentState.files.isEmpty()) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("No media found.")
                    }
                    return@Box
                }

                val pagerState = rememberPagerState(
                    initialPage = startIndex,
                    pageCount = { currentState.files.size }
                )

                // ✅ Update currentFileId when page changes
                LaunchedEffect(pagerState.currentPage, currentState.files) {
                    currentFileId = currentState.files.getOrNull(pagerState.currentPage)?.id
                }

                LaunchedEffect(pagerState.isScrollInProgress) {
                    if (pagerState.isScrollInProgress) {
                        zoomedPageIndex = -1
                    }
                }

                LaunchedEffect(pagerState.currentPage) {
                    if (pagerState.currentPage >= currentState.files.size - 10) {
                        viewModel.loadPage(currentState.currentPage + 1)
                    }
                }

                VerticalPager(
                    state = pagerState,
                    userScrollEnabled = isPagerScrollEnabled,
                    modifier = Modifier.fillMaxSize()
                ) { pageIndex ->
                    // Guard against index out of bounds if list shrinks
                    currentState.files.getOrNull(pageIndex)?.let { file ->
                        MediaSlide(
                            file = file,
                            activeApiUrl = currentState.activeApiUrl,
                            activeApiKey = currentState.activeApiKey,
                            onNextImage = { /* logic to go to next image */ },
                            onPreviousImage = { /* logic to go to previous image */ },
                            allowSwipeNavigation = true,
                            doubleTapZoomLevel = currentState.zoomLevel
                        )
                    }
                }
            }
            else -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Loading viewer...")
                }
            }
        }

        // ✅ Delete confirmation dialog
        if (showDeleteDialog != null) {
            AlertDialog(
                onDismissRequest = { showDeleteDialog = null },
                title = { Text("Delete File") },
                text = { Text("Are you sure you want to move this file to the recycle bin?") },
                confirmButton = {
                    TextButton(
                        onClick = {
                            showDeleteDialog?.let { viewModel.deleteMediaItem(it) }
                            showDeleteDialog = null
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

        // ✅ Delete Button
        IconButton(
            onClick = {
                // Show dialog for the currently visible file
                currentFileId?.let { showDeleteDialog = it }
            },
            modifier = Modifier
                .align(Alignment.TopStart) // Positioned at the top start
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