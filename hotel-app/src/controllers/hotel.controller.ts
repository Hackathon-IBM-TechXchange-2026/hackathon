import { HotelService, BookingInput } from '../services/hotel.service';

export interface HttpRequest {
  body: Record<string, unknown>;
  params?: Record<string, string>;
  headers?: Record<string, string>;
}

export interface HttpResponse {
  statusCode: number;
  body: unknown;
}

export class HotelController {
  constructor(private readonly hotelService: HotelService) {}

  public async handleCreateBooking(req: HttpRequest): Promise<HttpResponse> {
    const { guestId, roomId, checkIn, checkOut, metadata } = req.body;

    if (!guestId || !roomId || !checkIn || !checkOut) {
      return {
        statusCode: 400,
        body: { success: false, errorMessage: 'guestId, roomId, checkIn, and checkOut are required' },
      };
    }

    const input: BookingInput = {
      guestId: String(guestId),
      roomId: String(roomId),
      checkIn: new Date(checkIn as string),
      checkOut: new Date(checkOut as string),
      metadata: metadata as Record<string, unknown> | undefined,
    };

    try {
      const result = await this.hotelService.createBooking(input);
      if (!result.success) {
        return { statusCode: 422, body: result };
      }
      return { statusCode: 201, body: { success: true, data: result } };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      if (
        message.includes('not found') ||
        message.includes('not available') ||
        message.includes('Check-out must be')
      ) {
        return { statusCode: 400, body: { success: false, errorMessage: message } };
      }
      return { statusCode: 500, body: { success: false, errorMessage: 'Internal server error' } };
    }
  }

  public async handleCancelBooking(req: HttpRequest): Promise<HttpResponse> {
    const bookingId = req.params?.id;
    if (!bookingId) {
      return { statusCode: 400, body: { success: false, errorMessage: 'Booking ID is required' } };
    }

    const requestDate = req.body?.requestDate
      ? new Date(req.body.requestDate as string)
      : new Date();

    try {
      const result = await this.hotelService.cancelBooking(bookingId, requestDate);
      if (!result.success) {
        if (result.errorMessage?.includes('not found')) {
          return { statusCode: 404, body: result };
        }
        return { statusCode: 422, body: result };
      }
      return { statusCode: 200, body: { success: true, data: result } };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return { statusCode: 500, body: { success: false, errorMessage: message } };
    }
  }

  public async handleGetBooking(req: HttpRequest): Promise<HttpResponse> {
    const bookingId = req.params?.id;
    if (!bookingId) {
      return { statusCode: 400, body: { success: false, errorMessage: 'Booking ID is required' } };
    }

    try {
      const booking = await this.hotelService.getBooking(bookingId);
      if (!booking) {
        return { statusCode: 404, body: { success: false, errorMessage: `Booking ${bookingId} not found` } };
      }
      return { statusCode: 200, body: { success: true, data: booking } };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return { statusCode: 500, body: { success: false, errorMessage: message } };
    }
  }
}
