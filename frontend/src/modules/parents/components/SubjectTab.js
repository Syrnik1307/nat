import React from 'react';
import SummaryCards from './SummaryCards';
import HomeworkList from './HomeworkList';
import HomeworkChart from './HomeworkChart';
import ControlPoints from './ControlPoints';
import TeacherComments from './TeacherComments';
import KnowledgeMapStub from './KnowledgeMapStub';
import FinanceStub from './FinanceStub';

const SubjectTab = ({ subject, selectedMonth, onMonthChange }) => {
  if (!subject) return null;

  return (
    <div className="pd-subject">
      <p className="pd-teacher-name">Преподаватель: {subject.teacher_name}</p>

      <SummaryCards subject={subject} />

      <HomeworkChart chartData={subject.hw_chart_data} />

      <HomeworkList
        homeworkList={subject.homework_list}
        selectedMonth={selectedMonth}
        onMonthChange={onMonthChange}
      />

      {subject.control_points?.length > 0 && (
        <ControlPoints controlPoints={subject.control_points} />
      )}

      <KnowledgeMapStub data={subject.knowledge_map} />
      <FinanceStub data={subject.finance} />

      {subject.comments?.length > 0 && (
        <TeacherComments comments={subject.comments} />
      )}
    </div>
  );
};

export default SubjectTab;
