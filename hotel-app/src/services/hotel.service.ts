import {
  HotelRepository,
  BookingRecord,
  BookingStatus,
  RoomType,
} from '../repository/hotel.repository';

export interface BookingInput {
  guestId: string;
  roomId: string;
  checkIn: Date;
  checkOut: Date;
  metadata?: Record<string, unknown>;
}

export interface BookingResult {
  success: boolean;
  bookingId?: string;
  status: BookingStatus;
  nights: number;
  baseRate: number;
  cleaningFee: number;
  total: number;
  errorMessage?: string;
}

export interface CancelResult {
  success: boolean;
  refundAmount: number;
  refundPercentage: number;
  errorMessage?: string;
}

export class HotelService {
  private static readonly CLEANING_FEES: Record<RoomType, number> = {
    SINGLE: 30.0,
    DOUBLE: 50.0,
    SUITE: 80.0,
  };

  constructor(private readonly repository: HotelRepository) {}

  public calculateNights(checkIn: Date, checkOut: Date): number {
    // Use UTC calendar date difference to avoid DST/time-of-day discrepancies
    const checkInDay = Date.UTC(checkIn.getUTCFullYear(), checkIn.getUTCMonth(), checkIn.getUTCDate());
    const checkOutDay = Date.UTC(checkOut.getUTCFullYear(), checkOut.getUTCMonth(), checkOut.getUTCDate());
    const nights = Math.round((checkOutDay - checkInDay) / (1000 * 60 * 60 * 24));
    if (nights < 1) {
      throw new Error('Check-out must be at least 1 night after check-in');
    }
    return nights;
  }

  public calculateCleaningFee(roomType: RoomType): number {
    return HotelService.CLEANING_FEES[roomType];
  }

  public calculateRefund(booking: BookingRecord, cancellationDate: Date): number {
    const msUntilCheckIn = booking.checkIn.getTime() - cancellationDate.getTime();
    const hoursUntilCheckIn = msUntilCheckIn / (1000 * 60 * 60);

    if (hoursUntilCheckIn > 48) {
      return Number(booking.total.toFixed(2));
    } else if (hoursUntilCheckIn >= 24) {
      return Number((booking.total * 0.5).toFixed(2));
    } else {
      return 0;
    }
  }

  public async validateBookingInput(input: BookingInput): Promise<void> {
    if (!input.guestId || input.guestId.trim().length === 0) {
      throw new Error('Guest ID is required');
    }
    if (!input.roomId || input.roomId.trim().length === 0) {
      throw new Error('Room ID is required');
    }
    if (!(input.checkIn instanceof Date) || isNaN(input.checkIn.getTime())) {
      throw new Error('Check-in date is invalid');
    }
    if (!(input.checkOut instanceof Date) || isNaN(input.checkOut.getTime())) {
      throw new Error('Check-out date is invalid');
    }

    // calculateNights throws if checkOut <= checkIn
    this.calculateNights(input.checkIn, input.checkOut);

    const room = await this.repository.findRoomById(input.roomId);
    if (!room) {
      throw new Error(`Room ${input.roomId} not found`);
    }
    if (!room.available) {
      throw new Error(`Room ${input.roomId} is not available`);
    }
  }

  public async createBooking(input: BookingInput): Promise<BookingResult> {
    await this.validateBookingInput(input);

    const room = await this.repository.findRoomById(input.roomId);
    if (!room) {
      return { success: false, status: 'PENDING', nights: 0, baseRate: 0, cleaningFee: 0, total: 0, errorMessage: 'Room not found' };
    }

    const nights = this.calculateNights(input.checkIn, input.checkOut);
    const baseRate = Number((nights * room.pricePerNight).toFixed(2));
    const cleaningFee = this.calculateCleaningFee(room.type);
    const total = Number((baseRate + cleaningFee).toFixed(2));

    await this.repository.updateRoomAvailability(input.roomId, false);

    const record = await this.repository.createBooking({
      guestId: input.guestId,
      roomId: input.roomId,
      checkIn: input.checkIn,
      checkOut: input.checkOut,
      nights,
      baseRate,
      cleaningFee,
      total,
      metadata: input.metadata,
    });

    return {
      success: true,
      bookingId: record.id,
      status: record.status,
      nights,
      baseRate,
      cleaningFee,
      total,
    };
  }

  public async cancelBooking(bookingId: string, requestDate: Date): Promise<CancelResult> {
    const booking = await this.repository.findBookingById(bookingId);
    if (!booking) {
      return { success: false, refundAmount: 0, refundPercentage: 0, errorMessage: `Booking ${bookingId} not found` };
    }

    if (booking.status === 'CANCELLED') {
      return { success: false, refundAmount: 0, refundPercentage: 0, errorMessage: 'Booking is already cancelled' };
    }
    if (booking.status === 'COMPLETED') {
      return { success: false, refundAmount: 0, refundPercentage: 0, errorMessage: 'Completed bookings cannot be cancelled' };
    }

    const refundAmount = this.calculateRefund(booking, requestDate);
    const refundPercentage = booking.total > 0 ? Math.round((refundAmount / booking.total) * 100) : 0;

    await this.repository.updateBookingStatus(bookingId, 'CANCELLED');
    await this.repository.updateRoomAvailability(booking.roomId, true);

    return { success: true, refundAmount, refundPercentage };
  }

  public async getBooking(id: string): Promise<BookingRecord | null> {
    return this.repository.findBookingById(id);
  }
}
