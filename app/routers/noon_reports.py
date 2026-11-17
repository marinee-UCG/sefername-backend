from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


from app.core.deps import get_current_user
from app.models.user import User
from app.services.noon_track import with_distances
from app.database import get_db
from app.models.noon_report import NoonReport
from app.models.voyage import Voyage
from app.routers.voyages import get_user_voyage_or_404
from app.schemas.noon_report import NoonReportCreate, NoonReportOut, NoonReportUpdate
from app.services.weather import noon_weather

router=APIRouter(tags=["noon-reports"])

def get_user_noon_report_or_404(
        report_id:int,
        current_user:User=Depends(get_current_user),
        db:Session=Depends(get_db)
):
    query=select(NoonReport).where(NoonReport.id==report_id,NoonReport.user_id==current_user.id)
    report=db.scalar(query)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Noon report not found"
        )
    return report
def check_noon_time(
        voyage:Voyage,
        recorded_at:datetime
) -> None :
    if recorded_at < voyage.cosp_at:
        raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Noon report cannot be before COSP"
            )
    if voyage.eosp_at is not None and recorded_at > voyage.eosp_at:
        raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Noon report cannot be after EOSP"
            )
    if recorded_at> datetime.now(UTC) + timedelta(minutes=5):
        raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Noon report cannot be in the future"
            )


@router.post("/voyages/{voyage_id}/noon-reports",response_model=NoonReportOut,status_code=status.HTTP_201_CREATED)
def create_noon_report(
    report_in:NoonReportCreate,
    voyage:Voyage=Depends(get_user_voyage_or_404),
    db:Session=Depends(get_db)
):
    check_noon_time(voyage,report_in.recorded_at)

    ship_date=report_in.recorded_at.date()
    existing_report=db.scalar(select(NoonReport).where(NoonReport.voyage_id == voyage.id,NoonReport.ship_date==ship_date))
    if existing_report is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is already a noon report for this day. Edit it instead"
        )
    weather=noon_weather(report_in.lat,report_in.lon,report_in.recorded_at)
    report=NoonReport(
        user_id=voyage.user_id,
        voyage_id=voyage.id,
        recorded_at=report_in.recorded_at,
        ship_date=ship_date,
        lat=report_in.lat,
        lon=report_in.lon,
        note=report_in.note,
        wind_bft=weather.wind_bft,
        wind_dir_deg=weather.wind_dir_deg,
        wave_m=weather.wave_m
    )
    db.add(report)
    try:    
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is already a noon report for this day. Edit it instead"
        )
    db.refresh(report)
    reports=db.scalars(select(NoonReport).where(NoonReport.voyage_id==voyage.id)).all()
    for item in with_distances(voyage,reports):
        if item["id"]==report.id:
            return item

@router.get("/voyages/{voyage_id}/noon-reports",response_model=list[NoonReportOut])
def list_noon_reports(
    voyage:Voyage=Depends(get_user_voyage_or_404),
    db:Session=Depends(get_db)
):
    query=select(NoonReport).where(NoonReport.voyage_id==voyage.id)
    reports=db.scalars(query).all()
    return with_distances(voyage,reports)


@router.patch("/noon-reports/{report_id}",response_model=NoonReportOut)
def update_noon_report(
    report_in:NoonReportUpdate,
    report:NoonReport=Depends(get_user_noon_report_or_404),
    db:Session=Depends(get_db)
):
    update_data=report_in.model_dump(exclude_unset=True)
    # Time and position cannot be emptied; the note can
    for field in ("recorded_at","lat","lon"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null."
            )

    voyage=db.get(Voyage,report.voyage_id)
    if "recorded_at" in update_data:
        check_noon_time(voyage,update_data["recorded_at"])
        new_day=update_data["recorded_at"].date()
        # Moved to another ship day: that day must not have a report already
        if new_day!=report.ship_date:
            existing_report=db.scalar(select(NoonReport).where(NoonReport.voyage_id==voyage.id,NoonReport.ship_date==new_day))
            if existing_report is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="There is already a noon report for this day. Edit it instead"
                )
        report.ship_date=new_day

    for key,value in update_data.items():
        setattr(report,key,value)

    # A new time or position makes the old weather wrong; a changed note alone does not
    if "recorded_at" in update_data or "lat" in update_data or "lon" in update_data:
        weather=noon_weather(report.lat,report.lon,report.recorded_at)
        report.wind_bft=weather.wind_bft
        report.wind_dir_deg=weather.wind_dir_deg
        report.wave_m=weather.wave_m

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is already a noon report for this day. Edit it instead"
        )
    db.refresh(report)
    reports=db.scalars(select(NoonReport).where(NoonReport.voyage_id==voyage.id)).all()
    for item in with_distances(voyage,reports):
        if item["id"]==report.id:
            return item


@router.delete("/noon-reports/{report_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_noon_report(
    report:NoonReport=Depends(get_user_noon_report_or_404),
    db:Session=Depends(get_db)
):
    db.delete(report)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
