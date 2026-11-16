package fixture

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

sealed interface Delivery {
    data object Editing : Delivery
    data object Sending : Delivery
    data class Sent(val receipt: String) : Delivery
}

fun interface Sender {
    suspend fun send(message: String): String
}

@Composable
fun MessagePanel(sender: Sender) {
    var message by remember { mutableStateOf("") }
    var delivery by remember { mutableStateOf<Delivery>(Delivery.Editing) }
    var longWait by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    LaunchedEffect(delivery) {
        if (delivery == Delivery.Sending) {
            delay(1_000)
            longWait = true
        }
    }
    Column {
        TextField(message, onValueChange = { message = it }, label = { Text("Message") })
        Button(
            enabled = delivery == Delivery.Editing && message.isNotBlank(),
            onClick = {
                scope.launch {
                    delivery = Delivery.Sending
                    delivery = Delivery.Sent(sender.send(message))
                }
            },
        ) { Text("Send") }
        when (val current = delivery) {
            Delivery.Editing -> Text("Ready to send")
            Delivery.Sending -> {
                Text("Sending")
                if (longWait) Text("Still sending")
            }
            is Delivery.Sent -> Text(current.receipt)
        }
    }
}

@Composable
fun MergedLabel() {
    Column(Modifier.testTag("summary").semantics(mergeDescendants = true) {}) {
        Text("Draft", Modifier.testTag("summary-child"))
        Text("Ready")
    }
}

@Composable
fun DraftActions(onOpen: (String) -> Unit) {
    Column {
        Column(Modifier.testTag("draft")) {
            Text("Draft")
            Button(onClick = { onOpen("Draft opened") }) { Text("Open") }
        }
        Column(Modifier.testTag("archive")) {
            Text("Archive")
            Button(onClick = { onOpen("Archive opened") }) { Text("Open") }
        }
    }
}
