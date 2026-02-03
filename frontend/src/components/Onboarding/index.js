/**
 * Onboarding Module - Lectio Space
 * 
 * Компоненты для интерактивных туров по интерфейсу
 * Использует библиотеку driver.js
 */

export { 
  // Базовые туры
  TeacherOnboarding, 
  StudentOnboarding, 
  SubscriptionOnboarding,
  HomeworkOnboarding,
  HomeworkConstructorOnboarding,
  RecordingsOnboarding,
  AnalyticsOnboarding,
  MarketOnboarding,
  StudentHomeworkOnboarding,
  StudentRecordingsOnboarding,
  
  // Детальные туры для домашних заданий
  HomeworkConstructorDetailedOnboarding,
  SubmissionReviewOnboarding,
  GradedSubmissionsListOnboarding,
  HomeworkTakeOnboarding,
  StudentAIReportsOnboarding,
  
  // Утилиты
  OnboardingTrigger,
} from './OnboardingManager';

export { useOnboarding } from './useOnboarding';

// Базовые конфигурации туров
export { 
  teacherTourSteps, 
  studentTourSteps,
  subscriptionTourSteps,
  homeworkTourSteps,
  homeworkConstructorTourSteps,
  recordingsTourSteps,
  analyticsTourSteps,
  marketTourSteps,
  studentHomeworkTourSteps,
  studentRecordingsTourSteps,
} from './tourConfig';

// Детальные конфигурации для домашних заданий
export {
  homeworkConstructorDetailedSteps,
  submissionReviewSteps,
  gradedSubmissionsListSteps,
  homeworkTakeSteps,
  studentAIReportsSteps,
  elementExists,
  filterExistingSteps,
} from './driverConfig';
