@smoke
Feature: Resume paste and save
  Candidates paste a resume so the agent can score fit and draft cover letters.

  Background:
    Given I open the resume page

  Scenario: Paste and save a resume
    When I paste a sample resume titled "Interview demo resume"
    And I save the resume
    Then I should see a resume saved confirmation
    And the resume content should persist in the session

  Scenario Outline: Reject too-short resume paste
    When I paste resume text "<text>"
    And I save the resume
    Then I should see resume validation feedback

    Examples:
      | text        |
      | short       |
      | almost ok   |
