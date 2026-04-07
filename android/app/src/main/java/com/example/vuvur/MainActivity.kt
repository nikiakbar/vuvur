package com.example.vuvur

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CropPortrait
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp // ✅ Import for sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.vuvur.screens.GalleryScreen
import com.example.vuvur.screens.LockScreen
import com.example.vuvur.screens.MediaViewModel
import com.example.vuvur.screens.RandomScreen
import com.example.vuvur.screens.SettingsScreen
import com.example.vuvur.screens.SingleMediaScreen
import com.example.vuvur.screens.ViewerScreen
import com.example.vuvur.ui.theme.VuvurTheme
import kotlinx.coroutines.launch

sealed class Screen(val route: String, val label: String, val icon: ImageVector) {
    data object Gallery : Screen("gallery", "Gallery", Icons.Default.Home)
    data object Random : Screen("random", "Random", Icons.Default.Shuffle)
    data object Single : Screen("single", "Single", Icons.Default.CropPortrait)
    data object Settings : Screen("settings", "Settings", Icons.Default.Settings)
    data object Viewer : Screen("viewer/{startIndex}", "Viewer", Icons.Default.Home)
}

val menuItems = listOf(
    Screen.Gallery,
    Screen.Random,
    Screen.Single,
    Screen.Settings
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            VuvurTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    AppNavigation()
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppNavigation() {
    var isUnlocked by remember { mutableStateOf(false) }

    if (!isUnlocked) {
        LockScreen(onUnlock = { isUnlocked = true })
    } else {
        val navController = rememberNavController()
        val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
        val scope = rememberCoroutineScope()

        val mediaViewModel: MediaViewModel = viewModel()
        val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    val route = currentDestination?.route
    val isFullscreen = route == Screen.Random.route || route == Screen.Single.route || route?.startsWith("viewer") == true
    val gesturesEnabled = !isFullscreen

    val snackbarHostState = remember { SnackbarHostState() }
    val uiState by mediaViewModel.uiState.collectAsState()

    LaunchedEffect(uiState) {
        if (uiState is GalleryUiState.Loading) {
            (uiState as GalleryUiState.Loading).apiUrl?.let { url ->
                snackbarHostState.showSnackbar("Connecting to $url...")
            }
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        gesturesEnabled = gesturesEnabled,
        drawerContent = {
            ModalDrawerSheet(modifier = Modifier.width(180.dp)) {
                Spacer(Modifier.height(12.dp))
                menuItems.forEach { screen ->
                    val selected = currentDestination?.hierarchy?.any { it.route == screen.route } == true
                    NavigationDrawerItem(
                        icon = { Icon(screen.icon, contentDescription = screen.label) },
                        label = { Text(screen.label) },
                        selected = selected,
                        onClick = {
                            scope.launch { drawerState.close() }
                            navController.navigate(screen.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding)
                    )
                }
            }
        }
    ) {
        Scaffold(
            snackbarHost = { SnackbarHost(snackbarHostState) },
            topBar = {
                if (!isFullscreen) {
                    TopAppBar(
                        title = {
                            val currentTitle = menuItems.find { item ->
                                currentDestination?.hierarchy?.any { it.route == item.route } == true
                            }?.label ?: "Vuvur"
                            val activeApiDisplay = when (val state = uiState) {
                                is GalleryUiState.Success -> state.activeApiAlias
                                is GalleryUiState.Loading -> state.apiAlias ?: ""
                                is GalleryUiState.Scanning -> state.activeApiAlias
                                is GalleryUiState.Error -> state.activeApiAlias
                            }
                            Text(
                                text = "$currentTitle - $activeApiDisplay",
                                fontSize = 18.sp
                            )
                        },
                        navigationIcon = {
                            IconButton(onClick = { scope.launch { drawerState.open() } }) {
                                Icon(Icons.Default.Menu, contentDescription = "Open Menu")
                            }
                        }
                    )
                }
            }
        ) { innerPadding ->
            NavHost(
                navController = navController,
                startDestination = Screen.Gallery.route,
                modifier = if (!isFullscreen) Modifier.padding(innerPadding) else Modifier.fillMaxSize()
            ) {
                composable(Screen.Gallery.route) {
                    GalleryScreen(
                        viewModel = mediaViewModel,
                        onImageClick = { index ->
                            navController.navigate("viewer/$index")
                        }
                    )
                }
                composable(Screen.Random.route) {
                    RandomScreen(
                        viewModel = mediaViewModel,
                        navController = navController
                    )
                }
                composable(Screen.Single.route) {
                    SingleMediaScreen(
                        viewModel = mediaViewModel,
                        navController = navController
                    )
                }
                composable(Screen.Settings.route) { SettingsScreen() }

                composable(
                    route = Screen.Viewer.route,
                    arguments = listOf(navArgument("startIndex") { type = NavType.IntType })
                ) { backStackEntry ->
                    ViewerScreen(
                        viewModel = mediaViewModel,
                        startIndex = backStackEntry.arguments?.getInt("startIndex") ?: 0,
                        navController = navController
                    )
                }
            }
        }
    }
    }
}