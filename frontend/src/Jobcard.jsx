import React from 'react';

const JobCard = ({ job, onClick }) => {
  return (
    <button onClick={onClick} className="job-card">
      <h2 className="job-title">{job.Titel}</h2>
      <p className="job-detail"><strong>Arbeitgeber:</strong> {job.Arbeitgeber}</p>
      <p className="job-detail"><strong>Ort / Arbeitsort:</strong> {job.Ort} / {job.Arbeitsort}</p>
      <p className="job-detail"><strong>Positionen:</strong> {job.Positionen}</p>
      <p className="job-detail"><strong>Branche/Fächer:</strong> {job['Branche/Fächer']}</p>
      <p className="job-detail"><strong>Arbeitszeit:</strong> {job.Arbeitszeit}</p>
      <p className="job-detail"><strong>Anstellungsart:</strong> {job.Anstellungsart}</p>
    </button>
  );
};

export default JobCard;