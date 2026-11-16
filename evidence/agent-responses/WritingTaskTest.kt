package fixture

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.mutableStateOf
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
    val composeRule = createComposeRule()

    @Test
    fun openingDraftDisplaysDraftResultNotArchiveResult() {
        val opened = mutableStateOf<String?>(null)
        composeRule.setContent {
            Column {
                DraftActions(onOpen = { opened.value = it })
                opened.value?.let { Text(it) }
            }
        }

        composeRule.onAllNodesWithText("Open").assertCountEquals(2)
        composeRule.onNodeWithText("Draft opened").assertDoesNotExist()
        composeRule.onNode(
            hasText("Open") and hasAnyAncestor(hasTestTag("draft")),
        ).performClick()

        composeRule.onNodeWithText("Draft opened").assertIsDisplayed()
        composeRule.onNodeWithText("Archive opened").assertDoesNotExist()
    }
}
