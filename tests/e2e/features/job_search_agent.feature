@smoke @agent
Feature: Job search agent
  Candidates run the agent for a role and location, watch a live step trace,
  and review attributed job cards with fit scores.

  Background:
    Given I have a saved sample resume in the session
    And I open the agent page

  Scenario Outline: Run agent for role and location
    When I set the agent role to "<role>" and location to "<location>"
    And I run the job search agent
    Then I should see a live step trace with tool calls
    And I should see job cards with fit scores and gaps
    And job cards should show Himalayas or Jobicy attribution
    And the Apply link on a job card should open the original board URL

    Examples:
      | role          | location     |
      | AI engineer   | philippines  |
      | ML engineer   | remote       |
