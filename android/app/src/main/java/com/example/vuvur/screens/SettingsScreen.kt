package com.example.vuvur.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: SettingsViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    var showApiDropdown by remember { mutableStateOf(false) }
    var showClearCacheDialog by remember { mutableStateOf(false) }

    val snackbarHostState = remember { SnackbarHostState() }

    val message = state.message
    LaunchedEffect(message) {
        if (message != null) {
            snackbarHostState.showSnackbar(message)
            viewModel.clearMessage()
        }
    }

    if (showClearCacheDialog) {
        AlertDialog(
            onDismissRequest = { showClearCacheDialog = false },
            title = { Text("Confirm Clear Cache") },
            text = { Text("Are you sure you want to clear all caches and re-scan? This action cannot be undone.") },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.runCacheCleanup()
                        showClearCacheDialog = false
                    }
                ) {
                    Text("Confirm")
                }
            },
            dismissButton = {
                TextButton(onClick = { showClearCacheDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbarHostState) }) { padding ->
        if (state.isLoading) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            return@Scaffold
        }

        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {

                Text("API Endpoint", style = MaterialTheme.typography.titleMedium)

                ExposedDropdownMenuBox(
                    expanded = showApiDropdown,
                    onExpandedChange = { showApiDropdown = !showApiDropdown }
                ) {
                    OutlinedTextField(
                        value = state.apiAliases[state.activeApi] ?: state.activeApi,
                        onValueChange = {},
                        label = { Text("Active API URL") },
                        readOnly = true,
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = showApiDropdown) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = showApiDropdown,
                        onDismissRequest = { showApiDropdown = false }
                    ) {
                        state.apiList.forEach { apiUrl ->
                            val alias = state.apiAliases[apiUrl] ?: apiUrl
                            DropdownMenuItem(
                                text = { Text(alias) },
                                onClick = {
                                    viewModel.saveSettings(apiUrl)
                                    showApiDropdown = false
                                }
                            )
                        }
                    }
                }

                Text("Double-Tap Zoom Level", style = MaterialTheme.typography.titleMedium)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Slider(
                        value = state.zoomLevel,
                        onValueChange = { viewModel.saveZoomLevel(it) },
                        // ✅ Change valueRange to start from 2f
                        valueRange = 2f..5f,
                        // ✅ Adjust steps for 0.5 increments
                        steps = 5,
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        text = "${(state.zoomLevel * 10).roundToInt() / 10f}x",
                        modifier = Modifier.padding(start = 16.dp)
                    )
                }
            }

            Button(
                onClick = { showClearCacheDialog = true },
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(16.dp)
                    .fillMaxWidth()
            ) {
                Text("Clear All Caches & Re-Scan")
            }
        }
    }
}