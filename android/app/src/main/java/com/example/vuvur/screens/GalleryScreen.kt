package com.example.vuvur.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow // Keep for top-level groups
import androidx.compose.foundation.lazy.items // Keep for LazyRow/LazyGrid
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.foundation.lazy.staggeredgrid.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.KeyboardArrowDown // Icon for dropdown
import androidx.compose.material.icons.filled.KeyboardArrowUp // Icon for dropdown
import androidx.compose.material.icons.filled.Search
// ✅ Use the correct M3 imports
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedButton
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton // Use OutlinedButton for dropdown anchor
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow // For dropdown button text
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.example.vuvur.GalleryUiState
import com.example.vuvur.GroupInfo
import com.example.vuvur.MediaFile

@OptIn(ExperimentalMaterial3Api::class) // Keep OptIn
@Composable
fun GalleryScreen(
    viewModel: MediaViewModel,
    onImageClick: (Int) -> Unit
) {
    val state by viewModel.uiState.collectAsState()
    // Use the simpler 'is refreshing' check
    val isRefreshing = state is GalleryUiState.Loading && (state as GalleryUiState.Loading).apiUrl == null
    val pullRefreshState = rememberPullToRefreshState()

    var searchQuery by remember { mutableStateOf("") }
    var sortMenuExpanded by remember { mutableStateOf(false) }
    val sortOptions = mapOf(
        "random" to "Random",
        "date_asc" to "Older first",
        "date_desc" to "Newest first"
    )
    val focusManager = LocalFocusManager.current
    var showDeleteDialog by remember { mutableStateOf<Int?>(null) }

    // State for subgroup dropdown menu
    var subgroupMenuExpanded by remember { mutableStateOf(false) }

    // Dialog for Delete Confirmation (remains the same)
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

    // ✅ This is the PullToRefreshBox you started
    PullToRefreshBox(
        isRefreshing = isRefreshing,
        onRefresh = { viewModel.refresh() },
        modifier = Modifier.fillMaxSize(),
        state = pullRefreshState
    ) {
        // ✅ The rest of the screen content goes inside a Column here
        Column(modifier = Modifier.fillMaxSize()) {
            // Search and Sort Row (remains the same)
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = searchQuery,
                        onValueChange = { searchQuery = it },
                        label = { Text("Search using tags") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        leadingIcon = {
                            IconButton(onClick = {
                                viewModel.applySearch(searchQuery)
                                focusManager.clearFocus()
                            }) {
                                Icon(Icons.Default.Search, contentDescription = "Search by tags")
                            }
                        },
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                        keyboardActions = KeyboardActions(
                            onSearch = {
                                viewModel.applySearch(searchQuery)
                                focusManager.clearFocus()
                            }
                        )
                    )

                    IconButton(onClick = { sortMenuExpanded = true }) {
                        Icon(Icons.Default.ArrowDropDown, contentDescription = "Sort Options")
                    }
                }

                // Dropdown Menu for Sorting (aligned to the end)
                Box(modifier = Modifier.align(Alignment.TopEnd)) {
                    DropdownMenu(
                        expanded = sortMenuExpanded,
                        onDismissRequest = { sortMenuExpanded = false }
                    ) {
                        sortOptions.forEach { (key, value) ->
                            DropdownMenuItem(
                                text = { Text(value) },
                                onClick = {
                                    viewModel.applySort(key)
                                    sortMenuExpanded = false
                                }
                            )
                        }
                    }
                }
            }

            // Top-Level Group Buttons (LazyRow - remains the same)
            if (state is GalleryUiState.Success) {
                val successState = state as GalleryUiState.Success
                if (successState.groups.isNotEmpty()) {
                    LazyRow(
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        item {
                            QuickAccessButton(
                                text = "All",
                                isSelected = successState.selectedGroupTag == null,
                                onClick = {
                                    println("!!! Clicked 'All' button. Calling viewModel.applyGroupFilter(null)...")
                                    subgroupMenuExpanded = false // Close subgroup menu if open
                                    viewModel.applyGroupFilter(null)
                                }
                            )
                        }
                        items(successState.groups, key = { it.groupTag }) { group ->
                            QuickAccessButton(
                                text = "${group.groupTag} (${group.count})",
                                isSelected = successState.selectedGroupTag == group.groupTag,
                                onClick = {
                                    println("!!! Clicked group button: ${group.groupTag}. Calling viewModel.applyGroupFilter...")
                                    subgroupMenuExpanded = false // Close subgroup menu if open
                                    viewModel.applyGroupFilter(group.groupTag)
                                }
                            )
                        }
                    }
                }

                // Subgroup Dropdown Area (only show if a group is selected)
                if (successState.selectedGroupTag != null) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp, vertical = 4.dp),
                        contentAlignment = Alignment.CenterStart // Align dropdown button to the start
                    ) {
                        val buttonText = if (successState.isLoadingSubgroups) {
                            "Loading Subfolders..."
                        } else if (successState.selectedSubgroupTag != null) {
                            successState.selectedSubgroupTag // Show selected subgroup
                        } else {
                            "All '${successState.selectedGroupTag}'" // Show "All [Group]"
                        }
                        val dropdownIcon = if (subgroupMenuExpanded) Icons.Filled.KeyboardArrowUp else Icons.Filled.KeyboardArrowDown

                        // Button to anchor and trigger the dropdown
                        OutlinedButton(
                            onClick = { if (!successState.isLoadingSubgroups) subgroupMenuExpanded = true },
                            enabled = !successState.isLoadingSubgroups && successState.subgroups.isNotEmpty(), // Disable if loading or no subgroups
                            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                            modifier = Modifier.fillMaxWidth(0.6f) // Limit width of button
                        ) {
                            Text(
                                text = buttonText,
                                overflow = TextOverflow.Ellipsis, // Ellipsize if text too long
                                maxLines = 1,
                                modifier = Modifier.weight(1f) // Allow text to take available space
                            )
                            Spacer(Modifier.width(8.dp)) // Space before icon
                            Icon(dropdownIcon, contentDescription = "Select Subfolder")
                        }

                        // The Dropdown Menu itself
                        DropdownMenu(
                            expanded = subgroupMenuExpanded,
                            onDismissRequest = { subgroupMenuExpanded = false }
                        ) {
                            // "All [Group]" item
                            DropdownMenuItem(
                                text = { Text("All '${successState.selectedGroupTag}'") },
                                onClick = {
                                    viewModel.applySubgroupFilter(null)
                                    subgroupMenuExpanded = false
                                }
                            )
                            // Items for each subgroup
                            successState.subgroups.forEach { subgroupName ->
                                DropdownMenuItem(
                                    text = { Text(subgroupName) },
                                    onClick = {
                                        viewModel.applySubgroupFilter(subgroupName)
                                        subgroupMenuExpanded = false
                                    }
                                )
                            }
                        }
                    }
                }
            }


            // This Box handles the main content (grid, loading, errors)
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .weight(1f), // Allow this Box to take remaining space
                contentAlignment = Alignment.Center
            ) {
                when (val currentState = state) {
                    is GalleryUiState.Success -> {
                        if (currentState.files.isEmpty()) {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center,
                                modifier = Modifier.fillMaxSize().padding(16.dp)
                                    .verticalScroll(rememberScrollState())
                            ) {
                                Text("No media found.")
                                Spacer(Modifier.height(8.dp))
                                Text("(Pull down to refresh)")
                            }
                        } else {
                            GalleryGrid(
                                files = currentState.files,
                                activeApiUrl = currentState.activeApiUrl,
                                activeApiKey = currentState.activeApiKey, // Pass key
                                onScrolledToEnd = {
                                    if (!currentState.isLoadingNextPage && currentState.currentPage < currentState.totalPages) {
                                        viewModel.loadPage(currentState.currentPage + 1)
                                    }
                                },
                                onImageClick = onImageClick,
                                onDeleteClick = { fileId -> showDeleteDialog = fileId }
                            )
                            if (currentState.isLoadingNextPage) {
                                CircularProgressIndicator(modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp))
                            }
                        }
                    }
                    is GalleryUiState.Error -> {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center,
                            modifier = Modifier.fillMaxSize().padding(16.dp)
                                .verticalScroll(rememberScrollState())
                        ) {
                            Text("Failed to load: ${currentState.message}")
                            Spacer(Modifier.height(8.dp))
                            Text("(Pull down to refresh)")
                        }
                    }
                    is GalleryUiState.Scanning -> {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center,
                            modifier = Modifier.fillMaxSize().padding(16.dp)
                                .verticalScroll(rememberScrollState())
                        ) {
                            Text("Scanning Library...", style = MaterialTheme.typography.headlineSmall)
                            Spacer(Modifier.height(8.dp))
                            Text(
                                "Please wait, this may take a few minutes for a large collection.",
                                textAlign = TextAlign.Center
                            )
                            Spacer(Modifier.height(16.dp))
                            Text("${currentState.progress} / ${currentState.total} files scanned")
                            Spacer(Modifier.height(8.dp))
                            CircularProgressIndicator(modifier = Modifier.size(24.dp))
                        }
                    }
                    is GalleryUiState.Loading -> {
                        // Show a loading indicator *unless* it's a pull-to-refresh
                        if (currentState.apiUrl != null) {
                            CircularProgressIndicator()
                        }
                    }
                }
            }
        }
    }
}

// QuickAccessButton Composable - No changes needed
@Composable
fun QuickAccessButton(
    text: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    val colors = if (isSelected) {
        ButtonDefaults.elevatedButtonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary
        )
    } else {
        ButtonDefaults.elevatedButtonColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
            contentColor = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
    ElevatedButton(
        onClick = onClick,
        shape = RoundedCornerShape(16.dp), // Pill shape
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp), // Adjust padding
        colors = colors
    ) {
        Text(text)
    }
}


// GalleryGrid Composable
@Composable
fun GalleryGrid(
    files: List<MediaFile>,
    activeApiUrl: String,
    activeApiKey: String?, // Accept key
    onScrolledToEnd: () -> Unit,
    onImageClick: (Int) -> Unit,
    onDeleteClick: (Int) -> Unit
) {
    LazyVerticalStaggeredGrid(
        columns = StaggeredGridCells.Adaptive(150.dp),
        modifier = Modifier.fillMaxSize(), // Grid fills its available space
        contentPadding = PaddingValues(4.dp),
        verticalItemSpacing = 4.dp,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        itemsIndexed(files, key = { _, file -> file.id }) { index, file ->
            if (index >= files.size - 10) {
                LaunchedEffect(Unit) {
                    onScrolledToEnd()
                }
            }
            MediaThumbnail(
                file = file,
                activeApiUrl = activeApiUrl,
                activeApiKey = activeApiKey, // Pass key
                onClick = { onImageClick(index) },
                onDeleteClick = { onDeleteClick(file.id) }
            )
        }
    }
}


// MediaThumbnail Composable - No changes needed
@Composable
fun MediaThumbnail(
    file: MediaFile,
    activeApiUrl: String,
    activeApiKey: String?,
    onClick: () -> Unit,
    onDeleteClick: () -> Unit
) {
    val thumbnailUrl = "$activeApiUrl/api/thumbnails/${file.id}"
    val aspectRatio = if (file.height > 0 && file.width > 0) {
        file.width.toFloat() / file.height.toFloat()
    } else {
        1.0f
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(aspectRatio)
            .clickable { onClick() }
    ) {
        AsyncImage(
            model = ImageRequest.Builder(LocalContext.current)
                .data(thumbnailUrl)
                .apply {
                    activeApiKey?.let {
                        addHeader("X-Api-Key", it)
                    }
                }
                .crossfade(true)
                .build(),
            contentDescription = file.path,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop
        )
        IconButton(
            onClick = onDeleteClick,
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(4.dp)
                .size(24.dp)
                .background(Color.Black.copy(alpha = 0.5f), shape = CircleShape)
        ) {
            Icon(
                Icons.Default.Delete,
                contentDescription = "Delete",
                tint = Color.White,
                modifier = Modifier.size(16.dp)
            )
        }
    }
}