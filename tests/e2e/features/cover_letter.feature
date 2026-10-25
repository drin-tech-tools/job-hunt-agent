@agent
Feature: Cover letter draft
  After an agent run, candidates can open a drafted cover letter from a job card.

  Background:
    Given I have a saved sample resume in the session
    And I open the agent page

  Scenario: Open cover letter from a scored job
    When I run the job search agent
    Then I should see job cards with fit scores and gaps
    When I open the cover letter on the first job card
    Then I should see the cover letter modal with a subject and body
    And I can close the cover letter modal
