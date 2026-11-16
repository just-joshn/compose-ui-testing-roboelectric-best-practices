package fixture

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasSetTextAction
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

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class ReviewTaskTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun openingDraftDisplaysDraftResultNotArchiveResult() {
        compose.setContent {
            MaterialTheme {
                var result by remember { mutableStateOf("Nothing opened") }
                Column {
                    DraftActions { result = it }
                    Text(result)
                }
            }
        }

        compose.onNodeWithText("Nothing opened").assertIsDisplayed()
        compose.onAllNodesWithText("Open").assertCountEquals(2)
        compose.onNode(hasText("Open") and hasAnyAncestor(hasTestTag("draft")))
            .performClick()

        compose.onNodeWithText("Draft opened").assertIsDisplayed()
        compose.onNodeWithText("Nothing opened").assertDoesNotExist()
        compose.onNodeWithText("Archive opened").assertDoesNotExist()
    }

    @Test
    fun sendingMessageStaysPendingUntilSenderReturnsReceipt() {
        val receipt = CompletableDeferred<String>()
        val requests = mutableListOf<String>()
        val sender = Sender { message ->
            requests.add(message)
            receipt.await()
        }
        try {
            compose.setContent {
                MaterialTheme { MessagePanel(sender) }
            }
            compose.onNodeWithText("Ready to send").assertIsDisplayed()
            compose.onNodeWithText("Send").assertIsNotEnabled()
            compose.onNode(hasText("Message") and hasSetTextAction())
                .performTextInput("Hello draft")
            compose.onNodeWithText("Send").assertIsEnabled().performClick()

            // The deferred, not a sleep or Compose clock, holds this interval open.
            compose.onNodeWithText("Sending").assertIsDisplayed()
            compose.onNodeWithText("Send").assertIsNotEnabled()
            compose.onNodeWithText("Ready to send").assertDoesNotExist()
            compose.onNodeWithText("Receipt: message accepted").assertDoesNotExist()
            compose.runOnIdle {
                assertEquals(listOf("Hello draft"), requests)
                check(receipt.complete("Receipt: message accepted"))
            }

            compose.onNodeWithText("Receipt: message accepted").assertIsDisplayed()
            compose.onNodeWithText("Sending").assertDoesNotExist()
            compose.onNodeWithText("Still sending").assertDoesNotExist()
            compose.onNodeWithText("Ready to send").assertDoesNotExist()
            compose.onNodeWithText("Send").assertIsNotEnabled()
        } finally {
            receipt.cancel()
        }
    }
}
