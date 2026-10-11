package com.example.vuvur.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.example.vuvur.GalleryUiState
import com.example.vuvur.components.MediaSlide

@Composable
fun SingleMediaScreen(
    viewModel: MediaViewModel,
    navController: NavController
) {
    val state by viewModel.uiState.collectAsState()
    var isZoomed by remember { mutableStateOf(false) }
    var currentIndex by remember { mutableStateOf(0) }

    // Reset zoom when switching images
    LaunchedEffect(currentIndex) {
        isZoomed = false
    }

    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        when (val currentState = state) {
            is GalleryUiState.Success -> {
                if (currentState.files.isEmpty()) {
                    Text("No media found.")
                    return
                }

                // Ensure valid index
                val validIndex = currentIndex.coerceIn(0, currentState.files.size - 1)
                val currentFile = currentState.files[validIndex]

                // Prefetch next page when close to end
                LaunchedEffect(currentIndex) {
                    if (currentIndex >= currentState.files.size - 5) {
                        viewModel.loadPage(currentState.currentPage + 1)
                    }
                }

                Column(
                    modifier = Modifier.fillMaxSize(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Box(modifier = Modifier.weight(1f)) {
                        MediaSlide(
                            file = currentFile,
                            activeApiUrl = currentState.activeApiUrl,
                            activeApiKey = currentState.activeApiKey,
                            onNextImage = { currentIndex++ },
                            onPreviousImage = { currentIndex-- },
                            allowSwipeNavigation = false, // disables vertical swipe
                            // ✅ Pass the zoom level from the state
                            doubleTapZoomLevel = currentState.zoomLevel
                        )

                        // Floating "Next" button (circle only, no text)
                        if (!isZoomed && validIndex < currentState.files.size - 1) {
                            IconButton(
                                onClick = { currentIndex++ },
                                modifier = Modifier
                                    .align(Alignment.CenterStart)
                                    .padding(12.dp)
                                    .size(40.dp) // circle size
                            ) {
                                Box(
                                    modifier = Modifier
                                        .fillMaxSize()
                                        .background(
                                            color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.3f),
                                            shape = CircleShape
                                        )
                                )
                            }
                        }

                    }

                    // Keep space at bottom so layout looks stable
                    Spacer(modifier = Modifier.height(36.dp))
                }
            }
            else -> {
                CircularProgressIndicator()
            }
        }
    }
}