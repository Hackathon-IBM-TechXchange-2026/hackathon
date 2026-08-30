import { HotelRepository } from '../../src/repository/hotel.repository';
import { HotelService } from '../../src/services/hotel.service';
import { HotelController, HttpRequest } from '../../src/controllers/hotel.controller';

describe('Hotel Booking Integration Flow', () => {
  let repository: HotelRepository;
  let service: HotelService;
  let controller: HotelController;
  let roomId: string;

  beforeEach(async () => {
    repository = new HotelRepository();
    service = new HotelService(repository);
    controller = new HotelController(service);

    const room = await repository.createRoom({
      number: '301',
      type: 'SUITE',
      pricePerNight: 500,
      available: true,
    });
    roomId = room.id;
  });

  afterEach(async () => {
    await repository.clear();
  });

  // --- Create Booking ---
  describe('POST /bookings — handleCreateBooking', () => {
    it('should return 201 with booking data for valid input', async () => {
      const req: HttpRequest = {
        body: {
          guestId: 'guest_A',
          roomId,
          checkIn: '2025-12-15T14:00:00.000Z',
          checkOut: '2025-12-17T10:00:00.000Z',
        },
      };
      const res = await controller.handleCreateBooking(req);
      expect(res.statusCode).toBe(201);
      const body = res.body as { success: boolean; data: { nights: number; cleaningFee: number; total: number } };
      expect(body.success).toBe(true);
      expect(body.data.nights).toBe(2);
      expect(body.data.cleaningFee).toBe(80); // SUITE
      expect(body.data.total).toBe(1080);     // 2*500 + 80
    });

    it('should return 400 when required fields are missing', async () => {
      const req: HttpRequest = { body: { guestId: 'guest_A' } };
      const res = await controller.handleCreateBooking(req);
      expect(res.statusCode).toBe(400);
    });

    it('should return 400 when checkOut is before checkIn', async () => {
      const req: HttpRequest = {
        body: {
          guestId: 'guest_A',
          roomId,
          checkIn: '2025-12-17T14:00:00.000Z',
          checkOut: '2025-12-15T10:00:00.000Z',
        },
      };
      const res = await controller.handleCreateBooking(req);
      expect(res.statusCode).toBe(400);
    });

    it('should return 400 when room does not exist', async () => {
      const req: HttpRequest = {
        body: {
          guestId: 'guest_A',
          roomId: 'nonexistent_room',
          checkIn: '2025-12-15T14:00:00.000Z',
          checkOut: '2025-12-17T10:00:00.000Z',
        },
      };
      const res = await controller.handleCreateBooking(req);
      expect(res.statusCode).toBe(400);
    });

    it('should return 400 when room is not available', async () => {
      await repository.updateRoomAvailability(roomId, false);
      const req: HttpRequest = {
        body: {
          guestId: 'guest_A',
          roomId,
          checkIn: '2025-12-15T14:00:00.000Z',
          checkOut: '2025-12-17T10:00:00.000Z',
        },
      };
      const res = await controller.handleCreateBooking(req);
      expect(res.statusCode).toBe(400);
    });
  });

  // --- Get Booking ---
  describe('GET /bookings/:id — handleGetBooking', () => {
    it('should return 200 with booking data when booking exists', async () => {
      const createReq: HttpRequest = {
        body: {
          guestId: 'guest_B',
          roomId,
          checkIn: '2025-12-20T14:00:00.000Z',
          checkOut: '2025-12-22T10:00:00.000Z',
        },
      };
      const createRes = await controller.handleCreateBooking(createReq);
      const bookingId = (createRes.body as { data: { bookingId: string } }).data.bookingId;

      const getRes = await controller.handleGetBooking({ body: {}, params: { id: bookingId } });
      expect(getRes.statusCode).toBe(200);
      const body = getRes.body as { data: { id: string } };
      expect(body.data.id).toBe(bookingId);
    });

    it('should return 404 when booking does not exist', async () => {
      const res = await controller.handleGetBooking({ body: {}, params: { id: 'bad_id' } });
      expect(res.statusCode).toBe(404);
    });

    it('should return 400 when no booking ID is provided', async () => {
      const res = await controller.handleGetBooking({ body: {} });
      expect(res.statusCode).toBe(400);
    });
  });

  // --- Cancel Booking ---
  describe('PATCH /bookings/:id/cancel — handleCancelBooking', () => {
    let bookingId: string;

    beforeEach(async () => {
      const req: HttpRequest = {
        body: {
          guestId: 'guest_C',
          roomId,
          checkIn: '2025-12-20T14:00:00.000Z',
          checkOut: '2025-12-23T10:00:00.000Z',
        },
      };
      const res = await controller.handleCreateBooking(req);
      bookingId = (res.body as { data: { bookingId: string } }).data.bookingId;
    });

    it('should return 200 with 100% refund for cancellation >48h before check-in', async () => {
      const req: HttpRequest = {
        body: { requestDate: '2025-12-17T00:00:00.000Z' },
        params: { id: bookingId },
      };
      const res = await controller.handleCancelBooking(req);
      expect(res.statusCode).toBe(200);
      const body = res.body as { data: { refundPercentage: number } };
      expect(body.data.refundPercentage).toBe(100);
    });

    it('should return 404 when booking does not exist', async () => {
      const req: HttpRequest = {
        body: { requestDate: '2025-12-17T00:00:00.000Z' },
        params: { id: 'nonexistent' },
      };
      const res = await controller.handleCancelBooking(req);
      expect(res.statusCode).toBe(404);
    });

    it('should return 422 when trying to cancel an already cancelled booking', async () => {
      const cancelReq: HttpRequest = {
        body: { requestDate: '2025-12-17T00:00:00.000Z' },
        params: { id: bookingId },
      };
      await controller.handleCancelBooking(cancelReq);
      const res = await controller.handleCancelBooking(cancelReq);
      expect(res.statusCode).toBe(422);
    });

    it('should return 400 when no booking ID is provided', async () => {
      const res = await controller.handleCancelBooking({ body: {} });
      expect(res.statusCode).toBe(400);
    });
  });

  // --- Full end-to-end flow ---
  describe('Full booking lifecycle', () => {
    it('should complete the full create → get → cancel flow', async () => {
      // 1. Create
      const createRes = await controller.handleCreateBooking({
        body: {
          guestId: 'guest_D',
          roomId,
          checkIn: '2025-12-25T14:00:00.000Z',
          checkOut: '2025-12-28T10:00:00.000Z',
        },
      });
      expect(createRes.statusCode).toBe(201);
      const bookingId = (createRes.body as { data: { bookingId: string } }).data.bookingId;

      // 2. Get
      const getRes = await controller.handleGetBooking({ body: {}, params: { id: bookingId } });
      expect(getRes.statusCode).toBe(200);

      // 3. Cancel with full refund (>48h before Dec 25)
      const cancelRes = await controller.handleCancelBooking({
        body: { requestDate: '2025-12-22T00:00:00.000Z' },
        params: { id: bookingId },
      });
      expect(cancelRes.statusCode).toBe(200);
      const cancelData = (cancelRes.body as { data: { refundPercentage: number } }).data;
      expect(cancelData.refundPercentage).toBe(100);

      // 4. Room should be available again
      const room = await repository.findRoomById(roomId);
      expect(room?.available).toBe(true);
    });
  });
});
