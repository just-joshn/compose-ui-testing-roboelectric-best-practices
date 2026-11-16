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
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class WritingTaskTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun openingDraftDisplaysDraftResultAndNotArchiveResult() {
        compose.setContent {
            var opened by remember { mutableStateOf<String?>(null) }
            MaterialTheme {
                Column {
                    DraftActions(onOpen = { opened = it })
                    opened?.let { Text(it) }
                }
            }
        }

        compose.onAllNodesWithText("Open").assertCountEquals(2)
        compose.onNodeWithText("Draft opened").assertDoesNotExist()
        compose.onNodeWithText("Archive opened").assertDoesNotExist()

        compose.onNode(
            hasText("Open") and hasAnyAncestor(hasTestTag("draft"))
        ).performClick()

        compose.onNodeWithText("Draft opened").assertIsDisplayed()
        compose.onNodeWithText("Archive opened").assertDoesNotExist()
    }
}
