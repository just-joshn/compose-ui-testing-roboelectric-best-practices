package fixture

import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import kotlinx.coroutines.CompletableDeferred
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

private class ControlledSender : Sender {
    private val receipt = CompletableDeferred<String>()
    val messages = mutableListOf<String>()

    override suspend fun send(message: String): String {
        messages.add(message)
        return receipt.await()
    }

    fun complete(value: String) {
        check(receipt.complete(value))
    }
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class ReviewTaskTest {
    @get:Rule val compose = createComposeRule()

    @Test fun scopedOpenSelectsDraft() {
        compose.setContent {
            var result by remember { mutableStateOf("Nothing opened") }
            DraftActions { result = it }
            Text(result)
        }
        compose.onAllNodesWithText("Open").assertCountEquals(2)
        compose.onNode(hasText("Open") and hasAnyAncestor(hasTestTag("draft"))).performClick()
        compose.onNodeWithText("Draft opened").assertIsDisplayed()
        compose.onNodeWithText("Archive opened").assertDoesNotExist()
    }

    @Test fun sendShowsReceiptAfterCompletion() {
        val sender = ControlledSender()
        compose.setContent { MessagePanel(sender) }
        compose.onNodeWithText("Message").performTextInput("Hello")
        compose.onNodeWithText("Send").performClick()
        compose.onNodeWithText("Sending").assertIsDisplayed()
        compose.onNodeWithText("Delivered Hello").assertDoesNotExist()
        compose.runOnIdle {
            assertEquals(listOf("Hello"), sender.messages)
            sender.complete("Delivered Hello")
        }
        compose.waitUntil(timeoutMillis = 2_000) {
            compose.onAllNodesWithText("Delivered Hello").fetchSemanticsNodes().size == 1
        }
        compose.onNodeWithText("Delivered Hello").assertIsDisplayed()
        compose.onNodeWithText("Sending").assertDoesNotExist()
    }
}
