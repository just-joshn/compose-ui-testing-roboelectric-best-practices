package fixture

import androidx.compose.ui.test.assert
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class DebuggingTaskTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun summaryChildHasDraft() {
        compose.setContent { MergedLabel() }

        compose.onNodeWithTag("summary-child", useUnmergedTree = true)
            .assert(hasText("Draft"))
    }
}
