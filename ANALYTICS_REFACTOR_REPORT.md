# Analytics Refactoring Report

## Changes
- **Moved Analytics Access**: Relocated "AI Анализ" from individual Recording Cards to the Group Detail Modal.
- **New Location**: "Group Detail Modal" -> Tab "📝 Отчеты по урокам" (Lesson Reports).
- **Functionality**:
  - Requires selecting a group (from Teacher Home Page).
  - Shows list of lessons for that group.
  - Button "📊 Открыть отчет" opens the charts for the specific lesson.

## Technical Details
- Created `GroupLessonReportsTab` component.
- Updated `GroupDetailModal` to include the new tab.
- Removed button and logic from `RecordingCard`.
- Fixed `apiService.js` duplicate definition.

## Deployment
- Frontend build updated on `tp` server.
- No backend changes required (API remains same).
- Access instructions:
  1. Open Teacher Dashboard.
  2. Click on a Student Group.
  3. Select tab "📝 Отчеты по урокам".
  4. Select a lesson to view detailed charts.
