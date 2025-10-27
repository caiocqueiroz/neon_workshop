Feature: Sistema de Gestão Financeira Escolar
  As a school administrator
  I want to manage student invoices and payments
  So that I can track tuition fees and maintain accurate financial records

  Background:
    Given I am logged in as a school administrator
    And there is a student "João Silva" in the system
    And there is an active academic session "2024/2025"
    And there is an academic term "1st Term"
    And there is a student class "Grade 10A"

  Scenario: Create a new invoice for a student
    Given I am on the invoice creation page
    When I select student "João Silva"
    And I select session "2024/2025"
    And I select term "1st Term"
    And I select class "Grade 10A"
    And I set balance from previous term to "0"
    And I click "Save"
    Then I should see the invoice in the invoice list
    And the invoice status should be "active"

  Scenario: Add items to an invoice
    Given there is an active invoice for student "João Silva"
    When I edit the invoice
    And I add an item with description "Tuition Fee" and amount "1000"
    And I add an item with description "Library Fee" and amount "50"
    And I save the invoice
    Then the invoice should show total payable amount of "1050"
    And the invoice balance should be "1050"

  Scenario: Record a payment for an invoice
    Given there is an invoice with total amount "1050" for student "João Silva"
    When I create a receipt for the invoice
    And I enter payment amount "500"
    And I enter payment date "2024-10-24"
    And I enter comment "Partial payment"
    And I save the receipt
    Then the invoice balance should be "550"
    And the receipt should appear in the invoice details

  Scenario: Calculate invoice balance correctly
    Given there is an invoice for student "João Silva"
    And the invoice has balance from previous term of "200"
    And the invoice has items totaling "1000"
    And there are receipts totaling "800"
    Then the total amount payable should be "1200"
    And the total amount paid should be "800"
    And the current balance should be "400"

  Scenario: View invoice details
    Given there is an invoice for student "João Silva"
    When I view the invoice details
    Then I should see the student information
    And I should see the session and term information
    And I should see all invoice items with descriptions and amounts
    And I should see all receipts with payment dates and amounts
    And I should see the current balance

  Scenario: Update invoice information
    Given there is an active invoice for student "João Silva"
    When I update the invoice
    And I change the balance from previous term to "100"
    And I save the changes
    Then the invoice should reflect the updated balance
    And the total payable amount should be recalculated

  Scenario: Delete an invoice
    Given there is an invoice for student "João Silva"
    When I delete the invoice
    And I confirm the deletion
    Then the invoice should be removed from the system
    And I should be redirected to the invoice list

  Scenario: Create bulk invoices
    Given I am on the bulk invoice page
    When I select multiple students
    And I configure the invoice parameters
    And I submit the bulk creation
    Then invoices should be created for all selected students
    And each invoice should have the correct student information

  Scenario: Handle invoice with zero balance
    Given there is an invoice with total amount "500" for student "João Silva"
    When I record a payment of "500"
    Then the invoice balance should be "0"
    And the invoice should show as fully paid

  Scenario: Prevent overpayment validation
    Given there is an invoice with balance "300" for student "João Silva"
    When I try to record a payment of "400"
    Then the system should allow the overpayment
    And the balance should show as "-100" (credit balance)

  Scenario: View invoice list with filters
    Given there are multiple invoices in the system
    When I access the invoice list page
    Then I should see all invoices ordered by student and term
    And each invoice should show student name, session, term, and balance
    And I should be able to access individual invoice details