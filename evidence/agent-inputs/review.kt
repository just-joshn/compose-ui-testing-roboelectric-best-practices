package fixture

import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import kotlinx.coroutines.CompletableDeferred
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class CurrentFlow {
    @get:Rule val compose = createComposeRule()

    @Test fun openAndSend() {
        val receipt = CompletableDeferred<String>()
        compose.setContent {
            var result by remember { mutableStateOf("Nothing opened") }
            DraftActions { result = it }
            Text(result)
            MessagePanel(Sender { receipt.await() })
        }
        compose.onNodeWithText("Open").performClick()
        Thread.sleep(1_000)
        compose.onNodeWithText("Open").assertExists()
        compose.onNodeWithText("Send").performClick()
        compose.waitForIdle()
        compose.onNodeWithText("Send").assertExists()
    }
}
