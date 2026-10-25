@smoke @tracker
Feature: Application tracker
  Candidates save jobs and move them through the pipeline.

  Background:
    Given I have a saved sample resume in the session
    And I open the agent page
    And I run the job search agent
    And job cards are visible

  Scenario: Save a job and move status saved to applied to interview
    When I save the first job to the tracker
    And I open the tracker page
    Then I should see the job in the "saved" column
    When I move the tracked job status to "applied"
    Then I should see the job in the "applied" column
    When I move the tracked job status to "interview"
    Then I should see the job in the "interview" column
