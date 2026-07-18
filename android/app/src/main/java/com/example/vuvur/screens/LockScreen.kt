package com.example.vuvur.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.vuvur.DuressState
import kotlinx.coroutines.launch

@Composable
fun LockScreen(
    isSetupMode: Boolean = false,
    correctCode: String? = null,
    onUnlock: () -> Unit = {},
    onPasscodeSet: (String) -> Unit = {}
) {
    var enteredCode by rememberSaveable { mutableStateOf("") }
    var firstEntry by rememberSaveable { mutableStateOf("") }
    var isConfirming by rememberSaveable { mutableStateOf(false) }

    // Holds a confirmed palindrome passcode pending the user's decision in the warning dialog
    var pendingPalindromeCode by rememberSaveable { mutableStateOf<String?>(null) }

    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    val title = when {
        isSetupMode && !isConfirming -> "Create Passcode"
        isSetupMode && isConfirming  -> "Confirm Passcode"
        else                         -> "Enter Passcode"
    }

    // Palindrome warning dialog — shown only during setup when a palindrome is confirmed
    if (pendingPalindromeCode != null) {
        AlertDialog(
            onDismissRequest = {
                // User dismissed without choosing — treat as "choose different"
                pendingPalindromeCode = null
                enteredCode = ""
                firstEntry = ""
                isConfirming = false
            },
            title = { Text("Duress Mode Unavailable") },
            text = {
                Text(
                    "Your passcode reads the same forwards and backwards (palindrome), " +
                    "so a reversed duress code cannot be created.\n\n" +
                    "Duress mode lets you enter your passcode in reverse to show an empty app " +
                    "with no media and no network access.\n\n" +
                    "Would you like to use this passcode anyway, or choose a different one?"
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    // User accepts the palindrome passcode — proceed without duress mode
                    val code = pendingPalindromeCode ?: return@TextButton
                    pendingPalindromeCode = null
                    onPasscodeSet(code)
                }) {
                    Text("Use Anyway")
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    // User wants to pick a different passcode
                    pendingPalindromeCode = null
                    enteredCode = ""
                    firstEntry = ""
                    isConfirming = false
                }) {
                    Text("Choose Different")
                }
            }
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(title, fontSize = 24.sp)
            Spacer(modifier = Modifier.height(16.dp))
            OutlinedTextField(
                value = enteredCode,
                onValueChange = { },
                label = { Text("Passcode") },
                visualTransformation = PasswordVisualTransformation(),
                readOnly = true,
                modifier = Modifier.width(200.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            NumericKeypad(onKeyPress = { key ->
                if (key == "backspace") {
                    if (enteredCode.isNotEmpty()) {
                        enteredCode = enteredCode.dropLast(1)
                    }
                } else if (enteredCode.length < 6) {
                    enteredCode += key
                    if (enteredCode.length == 6) {
                        if (isSetupMode) {
                            if (!isConfirming) {
                                firstEntry = enteredCode
                                enteredCode = ""
                                isConfirming = true
                            } else {
                                if (enteredCode == firstEntry) {
                                    val code = enteredCode
                                    // Check for palindrome — duress mode won't work
                                    if (code == code.reversed()) {
                                        // Pause and warn the user via dialog before proceeding
                                        pendingPalindromeCode = code
                                        enteredCode = ""
                                    } else {
                                        onPasscodeSet(code)
                                    }
                                } else {
                                    scope.launch {
                                        snackbarHostState.showSnackbar("Passcodes do not match. Start over.")
                                    }
                                    enteredCode = ""
                                    firstEntry = ""
                                    isConfirming = false
                                }
                            }
                        } else {
                            when (DuressState.evaluate(enteredCode, correctCode ?: "")) {
                                DuressState.UnlockResult.Real -> {
                                    // Correct passcode — normal unlock
                                    onUnlock()
                                }
                                DuressState.UnlockResult.Duress -> {
                                    // Reversed passcode — activate duress mode silently,
                                    // then unlock so the UI looks completely normal
                                    onUnlock()
                                }
                                DuressState.UnlockResult.Wrong -> {
                                    scope.launch {
                                        snackbarHostState.showSnackbar("Incorrect passcode")
                                    }
                                    enteredCode = ""
                                }
                            }
                        }
                    }
                }
            })
            Spacer(modifier = Modifier.height(16.dp))
            Button(
                onClick = {
                    enteredCode = ""
                    if (isSetupMode) {
                        firstEntry = ""
                        isConfirming = false
                    }
                },
                modifier = Modifier.height(56.dp).width(120.dp)
            ) {
                Text("Clear", fontSize = 18.sp)
            }
        }
    }
}

@Composable
fun NumericKeypad(onKeyPress: (String) -> Unit) {
    val buttonModifier = Modifier.size(85.dp)
    val fontSize = 24.sp

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        (1..9).chunked(3).forEach { row ->
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                row.forEach { number ->
                    Button(
                        onClick = { onKeyPress(number.toString()) },
                        modifier = buttonModifier
                    ) {
                        Text(number.toString(), fontSize = fontSize)
                    }
                }
            }
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Spacer to align 0 in the middle
            Spacer(modifier = buttonModifier)
            Button(
                onClick = { onKeyPress("0") },
                modifier = buttonModifier
            ) {
                Text("0", fontSize = fontSize)
            }
            Button(
                onClick = { onKeyPress("backspace") },
                modifier = buttonModifier
            ) {
                Text("<-", fontSize = 18.sp)
            }
        }
    }
}
