@access @smoke
Feature: Access control (auth + RBAC)
  The app is invite-only with mandatory TOTP (AAL2). Clients are scoped to their
  own data; admins manage users and can see all tracker items.

  Scenario: Unauthenticated visitor is redirected to login
    Given I am logged out
    When I open the home page
    Then I should be on the login page

  Scenario: Client cannot open admin users page
    Given I am authenticated as a client
    When I open the admin users page
    Then I should see an admin forbidden message

  Scenario: Client cannot see another user's tracker items
    Given an admin has a tracker item titled "Other user secret job"
    And I am authenticated as a client
    When I visit the tracker as the current user
    Then I should not see tracker text "Other user secret job"
