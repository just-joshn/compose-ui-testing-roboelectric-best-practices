package fixture

import androidx.compose.material3.Text
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.ComposeContentTestRule
import androidx.compose.ui.test.junit4.createComposeRule as createV1ComposeRule
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.printToString
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

private class ControlledSender : Sender {
    private val receipt = CompletableDeferred<String>()
    val messages = mutableListOf<String>()
    var cancelled = false
        private set

    override suspend fun send(message: String): String {
        messages.add(message)
        try {
            return receipt.await()
        } catch (error: CancellationException) {
            cancelled = true
            throw error
        }
    }

    fun complete(value: String) {
        check(receipt.complete(value))
    }
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class FixtureUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun mergedLabelAndUnmergedChild() {
        compose.setContent { MergedLabel() }
        compose.onNodeWithTag("summary").assert(hasText("Draft")).assertIsDisplayed()
        compose.onNodeWithTag("summary-child").assertDoesNotExist()
        compose.onNodeWithTag("summary-child", useUnmergedTree = true).assertIsDisplayed()
    }

    @Test fun scopedOpenSelectsDraft() {
        compose.setContent {
            var result by remember { mutableStateOf("Nothing opened") }
            DraftActions { result = it }
            Text(result)
        }
        compose.onAllNodesWithText("Open").assertCountEquals(2)
        val ambiguity = assertThrows(AssertionError::class.java) {
            compose.onNodeWithText("Open").performClick()
        }
        println("scopedOpenSelectsDraft ambiguity\n${ambiguity.message}")
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

    @OptIn(ExperimentalCoroutinesApi::class)
    @Test fun composeClockDoesNotCompleteSender() {
        val sender = ControlledSender()
        compose.mainClock.autoAdvance = false
        compose.setContent { MessagePanel(sender) }
        compose.onNodeWithText("Message").performTextInput("Clock")
        compose.mainClock.advanceTimeByFrame()
        compose.onNodeWithText("Send").performClick()
        compose.mainClock.scheduler.runCurrent()
        compose.mainClock.advanceTimeByFrame()
        compose.onNodeWithText("Sending").assertIsDisplayed()
        compose.onNodeWithText("Still sending").assertDoesNotExist()
        compose.mainClock.advanceTimeBy(1_200)
        compose.onNodeWithText("Still sending").assertIsDisplayed()
        compose.onNodeWithText("Sending").assertIsDisplayed()
        compose.onNodeWithText("Clock delivered").assertDoesNotExist()
        compose.runOnIdle { sender.complete("Clock delivered") }
        compose.mainClock.scheduler.runCurrent()
        compose.mainClock.advanceTimeByFrame()
        compose.onNodeWithText("Clock delivered").assertIsDisplayed()
    }

    @Test fun disposalCancelsPendingSendAndFreshPanelIsIsolated() {
        val first = ControlledSender()
        val second = ControlledSender()
        val showFirst = mutableStateOf(true)
        compose.setContent {
            key(showFirst.value) { MessagePanel(if (showFirst.value) first else second) }
        }
        compose.onNodeWithText("Message").performTextInput("First")
        compose.onNodeWithText("Send").performClick()
        compose.onNodeWithText("Sending").assertIsDisplayed()
        compose.runOnIdle { showFirst.value = false }
        compose.onNodeWithText("Ready to send").assertIsDisplayed()
        compose.runOnIdle {
            assertTrue(first.cancelled)
            assertTrue(second.messages.isEmpty())
            first.complete("Stale receipt")
        }
        compose.onNodeWithText("Stale receipt").assertDoesNotExist()
        compose.onNodeWithText("Message").performTextInput("Second")
        compose.onNodeWithText("Send").performClick()
        compose.onNodeWithText("Sending").assertIsDisplayed()
        compose.runOnIdle {
            assertEquals(listOf("Second"), second.messages)
            assertFalse(second.cancelled)
            second.complete("Second delivered")
        }
        compose.waitUntil(timeoutMillis = 2_000) {
            compose.onAllNodesWithText("Second delivered").fetchSemanticsNodes().size == 1
        }
        compose.onNodeWithText("Second delivered").assertIsDisplayed()
        compose.onNodeWithText("Stale receipt").assertDoesNotExist()
    }

    @Test fun selectorFailureIncludesTreeDiagnostics() {
        compose.setContent { MergedLabel() }
        val error = assertThrows(AssertionError::class.java) {
            compose.onNodeWithTag("summary-child").assertExists()
        }
        println("selectorFailureIncludesTreeDiagnostics original assertion\n${error.message}")
        println("MERGED\n${compose.onRoot().printToString()}")
        println("UNMERGED\n${compose.onRoot(useUnmergedTree = true).printToString()}")
        compose.onNodeWithTag("summary-child", useUnmergedTree = true).assertIsDisplayed()
    }
}

abstract class EffectOrderProbe {
    abstract val compose: ComposeContentTestRule

    @Test fun effectStartOrder() {
        val events = mutableListOf<String>()
        compose.setContent {
            LaunchedEffect(Unit) { events.add("effect") }
            DisposableEffect(Unit) {
                events.add("apply")
                onDispose { }
            }
            Text("Probe")
        }
        compose.waitForIdle()
        println("${javaClass.simpleName} events=$events")
        compose.onNodeWithText("Probe").assertIsDisplayed()
        assertEquals(setOf("effect", "apply"), events.toSet())
    }
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
@Suppress("DEPRECATION")
class V1EffectOrderTest : EffectOrderProbe() {
    @get:Rule override val compose = createV1ComposeRule()
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class V2EffectOrderTest : EffectOrderProbe() {
    @get:Rule override val compose = createComposeRule()
}
