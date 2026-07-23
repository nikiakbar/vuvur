package com.example.vuvur.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.foundation.lazy.staggeredgrid.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import coil.compose.AsyncImage
import com.example.vuvur.data.OfflineMediaItem
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun OfflineGalleryScreen(
    viewModel: OfflineViewModel,
    navController: NavController
) {
    LaunchedEffect(Unit) {
        viewModel.loadIndex()
    }

    val offlineItems by viewModel.offlineItems.collectAsState()
    var showDeleteDialog by remember { mutableStateOf<OfflineMediaItem?>(null) }

    Box(modifier = Modifier.fillMaxSize()) {
        if (offlineItems.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No offline media saved yet.")
            }
        } else {
            LazyVerticalStaggeredGrid(
                columns = StaggeredGridCells.Adaptive(150.dp),
                contentPadding = PaddingValues(4.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                itemsIndexed(offlineItems, key = { _, item -> item.id }) { index, item ->
                    OfflineGalleryItem(
                        item = item,
                        onClick = {
                            navController.navigate("offline_viewer/$index")
                        },
                        onDeleteClick = {
                            showDeleteDialog = item
                        }
                    )
                }
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
    }
}

@Composable
fun OfflineGalleryItem(
    item: OfflineMediaItem,
    onClick: () -> Unit,
    onDeleteClick: () -> Unit
) {
    val aspectRatio = if (item.width > 0 && item.height > 0) item.width.toFloat() / item.height.toFloat() else 1f

    // Format date and size
    val dateFormat = SimpleDateFormat("MMM dd, yyyy", Locale.getDefault())
    val dateString = dateFormat.format(Date(item.savedAt))
    val sizeString = formatSize(item.sizeBytes)

    Box(
        modifier = Modifier
            .padding(4.dp)
            .fillMaxWidth()
            .aspectRatio(aspectRatio.coerceIn(0.5f, 2.0f))
            .background(Color.DarkGray, RoundedCornerShape(8.dp))
            .clickable(onClick = onClick)
    ) {
        if (item.type.lowercase().let { it == "image" || it == "gif" }) {
            AsyncImage(
                model = item,
                contentDescription = "Offline Image",
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize()
            )
        } else {
            // Placeholder for video
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = Icons.Default.Delete, // TODO: Use better icons if available
                        contentDescription = "Video",
                        tint = Color.White,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    Text(
                        text = "Video",
                        color = Color.White,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }

        // Overlay with info
        Column(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .fillMaxWidth()
                .background(Color.Black.copy(alpha = 0.6f))
                .padding(8.dp)
        ) {
            Text(
                text = dateString,
                color = Color.White,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = sizeString,
                color = Color.LightGray,
                style = MaterialTheme.typography.labelSmall
            )
        }

        // Delete button
        IconButton(
            onClick = onDeleteClick,
            modifier = Modifier.align(Alignment.TopEnd)
        ) {
            Icon(
                Icons.Default.Delete,
                contentDescription = "Delete",
                tint = Color.White
            )
        }
    }
}

fun formatSize(bytes: Long): String {
    val kb = bytes / 1024.0
    val mb = kb / 1024.0
    return when {
        mb >= 1.0 -> String.format("%.1f MB", mb)
        kb >= 1.0 -> String.format("%.0f KB", kb)
        else -> "$bytes B"
    }
}
