@agent
Feature: Agent guardrails
  The agent must stop at max steps and handle job-source or API failures gracefully
  without hanging the UI.

  Background:
    Given I have a saved sample resume in the session
    And I open the agent page

  Scenario: Agent stops at max steps
    When I set the agent goal to include "[max_steps]"
    And I run the job search agent
    Then the agent message should mention max steps
    And the step trace should not exceed the configured max steps

  Scenario: Job source failure shows a graceful message
    When I set the agent goal to include "[source_failure]"
    And I run the job search agent
    Then the agent message should mention that job sources are unavailable
    And I should not see scored job cards

  Scenario: API timeout is handled gracefully
    When I set the agent goal to include "[timeout]"
    And I run the job search agent
    Then the agent message should mention timeout
