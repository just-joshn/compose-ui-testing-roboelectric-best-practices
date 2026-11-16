package fixture

import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.printToString
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class ClearingSemanticsProbeTest {
    @get:Rule val compose = createComposeRule()

    @Test fun unmergedTreeRetainsClearedDescendant() {
        compose.setContent {
            Column(
                Modifier.testTag("cleared").clearAndSetSemantics {
                    contentDescription = "Replacement"
                },
            ) {
                Text("Original child", Modifier.testTag("cleared-child"))
            }
        }
        println("MERGED\n${compose.onRoot().printToString()}")
        println("UNMERGED\n${compose.onRoot(useUnmergedTree = true).printToString()}")
        compose.onNodeWithTag("cleared").assert(hasContentDescription("Replacement"))
        compose.onNodeWithTag("cleared-child").assertDoesNotExist()
        compose.onNodeWithTag("cleared-child", useUnmergedTree = true)
            .assert(hasText("Original child"))
    }
}
